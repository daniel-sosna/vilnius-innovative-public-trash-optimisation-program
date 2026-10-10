"""Measured pilot and explicitly approved chronological coarse-to-fine search."""
import gc
import logging
from pathlib import Path
import subprocess
import threading
import time

import numpy as np
import psutil
from sklearn.metrics import f1_score

from .common import (model_names, clean_config, object_digest, output_path, read_json,
                     resources, split_mask, versions, write_json)
from .features import verify_cache
from .modeling import fit_model, grid_candidates, refined_grid, sample_features, score_predictions


class PeakMemory:
    def __enter__(self):
        self.stop = threading.Event()
        self.peak = psutil.Process().memory_info().rss
        def monitor():
            while not self.stop.wait(.05):
                self.peak = max(self.peak, psutil.Process().memory_info().rss)
        self.thread = threading.Thread(target=monitor, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.stop.set()
        self.thread.join()
        self.peak_gib = self.peak / 2**30


def gpu_probe(config, train):
    result = {}
    try:
        inventory = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total,driver_version', '--format=csv,noheader'],
                                   capture_output=True, text=True, timeout=15)
        result['inventory'] = inventory.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired) as error:
        result['inventory_error'] = str(error)
    try:
        from catboost import CatBoostClassifier
        model = CatBoostClassifier(iterations=3, depth=2, loss_function='MultiClass', task_type='GPU',
                                   allow_writing_files=False, verbose=False, random_seed=config['seed'])
        model.fit(np.arange(200).reshape(-1, 1), np.arange(200) % 5)
        result['catboost_verified'] = True
    except Exception as error:
        result['catboost_verified'] = False
        result['catboost_error'] = f'{type(error).__name__}: {error}'[:600]
    return result


def run_pilot(config, args):
    feature_manifest = verify_cache(config)
    proposed_samples = {}
    for name, limit in [('tuning', config['sampling']['tuning_rows']), ('final_train', config['sampling']['final_rows'])]:
        preview = sample_features(config, config['final_train'] if name == 'final_train' else config['splits']['train'], limit, name=name)
        proposed_samples[name] = read_json(output_path(config, 'samples', f'{name}.json'))
        logging.info('Proposed %s subset: %s rows, %s strata, %s bins', name, len(preview), proposed_samples[name]['observed_strata'], proposed_samples[name]['bins'])
        del preview
        gc.collect()
    pilot = sample_features(config, config['splits']['train'], config['sampling']['pilot_rows'], name='pilot', stratified=False)
    boundary = config['folds'][0]['validation'][0]
    train = pilot.loc[pilot.date < boundary].copy()
    validation = pilot.loc[pilot.date >= boundary].copy()
    before = resources()
    records = []
    folder = output_path(config, 'pilot')
    folder.mkdir(parents=True, exist_ok=True)
    initialization_start = time.monotonic()
    gpu = gpu_probe(config, train)
    initialization_seconds = time.monotonic() - initialization_start
    if config['search']['device'].startswith('cuda') and not all(gpu.get(n + '_verified') for n in model_names(config) if n != 'random_forest'):
        raise ValueError('CUDA verification failed; select CPU, refresh model-only cache metadata and rerun the pilot')
    for name in model_names(config):
        params = grid_candidates(config['search']['coarse'][name])[0]
        params['n_estimators' if name != 'catboost' else 'iterations'] = 50 if name == 'random_forest' else 80
        with PeakMemory() as memory:
            bundle = fit_model(name, params, train, config, evaluation=validation if name != 'random_forest' else None, pilot=True)
            probabilities = bundle.predict_proba(validation)
        record = {**bundle.metadata, 'peak_rss_gib': memory.peak_gib, 'macro_f1': f1_score(validation.fill_level, probabilities.argmax(axis=1), average='macro', zero_division=0), 'model': name}
        records.append(record)
        # Pilot models are transient; metadata is sufficient for this run.
        logging.info('Pilot %s: %.2fs, peak RSS %.3f GiB, Macro F1 %.4f (training-period sample only)', name, record['duration_seconds'], memory.peak_gib, record['macro_f1'])
        del bundle, probabilities
        gc.collect()
        if memory.peak_gib > config['search']['max_process_memory_gib']:
            raise MemoryError('Pilot exceeded the confirmed process memory limit')
    estimates = estimate_fits(config, records, len(train))
    proposal = {'configuration_sha256': object_digest(clean_config(config)), 'configuration': clean_config(config),
                'feature_cache_sha256': feature_manifest['features_sha256'], 'initialization_seconds': initialization_seconds,
                'proposed_samples': proposed_samples,
                'coarse_candidates': {name: grid_candidates(config['search']['coarse'][name]) for name in model_names(config)},
                'refinement': {'random_forest': 'Winning coarse parameters; depth +/-2 (minimum2) x max_features sqrt/0.7',
                               'catboost': 'Winning coarse parameters; l2_leaf_reg3/8 x random_strength0.5/1.5'},
                'pilot_records': records, 'resources_before_pilot': before, 'resources_after_pilot': resources(),
                'gpu': gpu, 'estimates': estimates, 'search_fits': sum(e['search_fits'] for e in estimates),
                'selection_fits': len(model_names(config)), 'final_refits': len(model_names(config)), 'additional_unseen_site_fit': 1, 'completed_pilot_fits': len(records), 'completed_compatibility_probe_fits': sum(n != 'random_forest' for n in model_names(config)),
                'estimated_training_seconds': sum(e['estimated_search_seconds'] + 2 * e['estimated_final_fit_seconds'] for e in estimates) + max(e['estimated_final_fit_seconds'] for e in estimates),
                'estimate_limitations': 'Linear row/iteration scaling with factor 2 after library/CUDA warmup; depth, sampling and RAM pressure can increase actual time. Evaluation/explanations excluded.',
                'approval_required': True, 'versions': versions()}
    proposal['proposal_sha256'] = object_digest(proposal)
    write_json(output_path(config, 'search_proposal.json'), proposal)
    write_json(folder / 'report.json', {'records': records, 'gpu': gpu, 'resources': before})
    logging.info('Search proposal: %s; approval required before tune', output_path(config, 'search_proposal.json'))


def estimate_fits(config, records, training_rows):
    estimates = []
    for record in records:
        name = record['model']
        count = len(grid_candidates(config['search']['coarse'][name])) + 4
        iterations = max(p['n_estimators' if name != 'catboost' else 'iterations'] for p in grid_candidates(config['search']['coarse'][name]))
        pilot_iterations = record['parameters']['n_estimators' if name != 'catboost' else 'iterations']
        factor = config['sampling']['tuning_rows'] / training_rows
        # Conservative screening estimate, not a benchmark at the proposed scale/depth.
        per_fit = record['duration_seconds'] * factor * iterations / pilot_iterations * 2
        final_fit = record['duration_seconds'] * config['sampling']['final_rows'] / training_rows * iterations / pilot_iterations * 2
        estimates.append({'model': name, 'coarse_candidates': count - 4, 'refined_candidates': 4,
                          'folds': len(config['folds']), 'search_fits': count * len(config['folds']),
                          'estimated_search_seconds': per_fit * count * len(config['folds']),
                          'estimated_final_fit_seconds': final_fit})
    return estimates


def require_approval(config, approval_file):
    if not approval_file:
        raise ValueError('Expensive search requires --approval-json pointing to the user-approved proposal record; run tune --pilot first')
    proposal = read_json(output_path(config, 'search_proposal.json'))
    if object_digest({k: v for k, v in proposal.items() if k != 'proposal_sha256'}) != proposal.get('proposal_sha256'):
        raise ValueError('Search proposal content changed without a matching digest; regenerate and confirm the proposal')
    approval = read_json(approval_file)
    if approval.get('approved') is not True or approval.get('proposal_sha256') != proposal['proposal_sha256'] or not approval.get('user_confirmation'):
        raise ValueError('Approval must record the explicit user confirmation and exact proposal_sha256')
    if proposal['configuration_sha256'] != object_digest(clean_config(config)):
        raise ValueError('Configuration changed after pilot/approval; rerun pilot and confirm revised proposal')
    if proposal.get('feature_cache_sha256') != read_json(output_path(config, 'features_manifest.json'))['features_sha256']:
        raise ValueError('Feature dataset changed after the proposal; rerun pilot and obtain a new confirmation')
    return {**proposal, 'approval_record': approval}


def tune(config, args):
    if args.pilot:
        return run_pilot(config, args)
    approved = require_approval(config, args.approval_json)
    verify_cache(config)
    sample = sample_features(config, config['splits']['train'], config['sampling']['tuning_rows'], name='tuning')
    records = []
    best_by_model = {}
    started = time.monotonic()
    folder = output_path(config, 'search')
    folder.mkdir(parents=True, exist_ok=True)
    write_json(folder / 'run_metadata.json', approved)
    for name in model_names(config):
        best, best_score = None, -np.inf
        for phase in ['coarse', 'refined']:
            grid = config['search']['coarse'][name] if phase == 'coarse' else refined_grid(name, best)
            for candidate_index, params in enumerate(grid_candidates(grid)):
                scores, macro_scores, iterations = [], [], []
                for fold_index, fold in enumerate(config['folds']):
                    if time.monotonic() - started > config['search']['budget_seconds']:
                        raise RuntimeError('Confirmed search time budget exceeded; partial results preserved. Request a revised budget to resume.')
                    training = sample.loc[split_mask(sample, fold['train'])]
                    validation = sample.loc[split_mask(sample, fold['validation'])]
                    with PeakMemory() as memory:
                        bundle = fit_model(name, params, training, config, evaluation=validation if name != 'random_forest' else None)
                        probabilities = bundle.predict_proba(validation)
                        score = score_predictions(config, validation.fill_level, probabilities)
                        macro = f1_score(validation.fill_level, probabilities.argmax(axis=1), average='macro', zero_division=0)
                    record = {'model': name, 'phase': phase, 'candidate': candidate_index, 'fold': fold_index,
                              'parameters': params, 'macro_f1': macro, 'score': score,
                              'score_name': config.get('objective', 'macro_f1'), 'duration_seconds': bundle.metadata['duration_seconds'],
                              'peak_rss_gib': memory.peak_gib, 'effective_iterations': bundle.metadata['effective_iterations'],
                              'train_period': fold['train'], 'validation_period': fold['validation']}
                    records.append(record)
                    write_json(folder / 'fits.json', records)
                    if time.monotonic() - started > config['search']['budget_seconds']:
                        raise RuntimeError('Confirmed search time budget exceeded; partial fit records preserved')
                    if memory.peak_gib > config['search']['max_process_memory_gib']:
                        raise MemoryError('Confirmed process memory budget exceeded; results preserved. Revise the sample/budget explicitly.')
                    scores.append(score)
                    macro_scores.append(macro)
                    iterations.append(bundle.metadata['effective_iterations'])
                    del bundle
                    gc.collect()
                summary = {'model': name, 'phase': phase, 'candidate': candidate_index, 'parameters': params,
                           'mean_score': float(np.mean(scores)), 'std_score': float(np.std(scores)),
                           'score_name': config.get('objective', 'macro_f1'),
                           'mean_macro_f1': float(np.mean(macro_scores)), 'std_macro_f1': float(np.std(macro_scores)),
                           'refit_iterations': int(np.median(iterations))}
                write_json(folder / f'{name}_{phase}_{candidate_index}.json', summary)
                logging.info('Search %s %s %s: %s %.4f +/- %.4f', name, phase, candidate_index, summary['score_name'], summary['mean_score'], summary['std_score'])
                if summary['mean_score'] > best_score:
                    best, best_score = dict(params), summary['mean_score']
                    best_by_model[name] = summary
        write_json(folder / 'best_parameters.json', best_by_model)
    write_json(folder / 'complete.json', {'fits': len(records), 'duration_seconds': time.monotonic() - started,
                                          'configuration_sha256': object_digest(clean_config(config))})
