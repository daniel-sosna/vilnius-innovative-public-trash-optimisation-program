"""Streaming metrics, frozen selection, retrospective inference and explanations."""
from collections import defaultdict
import gc
import logging
import shutil

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from .common import (model_names, PROBABILITY_COLUMNS, clean_config, digest, object_digest,
                     output_path, read_json, source_path, versions, write_json, provenance)
from .features import CATEGORICAL, FEATURES, HISTORY, NUMERIC, quality_flags, registry_features, verify_cache
from .modeling import (baseline_probabilities, feature_batches, fit_model, group_baseline_table,
                       load_model, model_input, sample_features, validate_probabilities)
from .search import PeakMemory, require_approval


class Metrics:
    def __init__(self, threshold=None):
        self.cm = np.zeros((5, 5), dtype=np.int64)
        self.loss = 0.
        self.threshold = threshold
        self.binary_cm = np.zeros((2, 2), dtype=np.int64)

    def add(self, y, probabilities):
        p = validate_probabilities(probabilities)
        y = np.asarray(y, dtype=int)
        if not np.isin(y, range(5)).all() or len(y) != len(p):
            raise ValueError('Invalid evaluation target')
        predicted = p.argmax(axis=1)
        self.cm += np.bincount(y * 5 + predicted, minlength=25).reshape(5, 5)
        urgent = predicted >= 3 if self.threshold is None else p[:, 3:].sum(axis=1) >= self.threshold
        self.binary_cm += np.bincount((y >= 3).astype(int) * 2 + urgent, minlength=4).reshape(2, 2)
        self.loss += float(-np.log(np.clip(p[np.arange(len(y)), y], np.finfo(float).eps, 1)).sum())

    def report(self):
        cm = self.cm.astype(float)
        n = cm.sum()
        if n == 0:
            raise ValueError('No labeled evaluation observations')
        support, predicted = cm.sum(axis=1), cm.sum(axis=0)
        precision = np.divide(cm.diagonal(), predicted, out=np.zeros(5), where=predicted > 0)
        recall = np.divide(cm.diagonal(), support, out=np.zeros(5), where=support > 0)
        f1 = np.divide(2 * precision * recall, precision + recall, out=np.zeros(5), where=precision + recall > 0)
        distance = np.abs(np.arange(5)[:, None] - np.arange(5)[None, :])
        expected = np.outer(support, predicted) / n
        denominator = (expected * distance**2).sum()
        normalized = np.divide(cm, support[:, None], out=np.zeros((5, 5)), where=support[:, None] > 0)
        tp = cm[3:, 3:].sum()
        bp = tp / predicted[3:].sum() if predicted[3:].sum() else 0.
        br = tp / support[3:].sum() if support[3:].sum() else 0.
        argmax_bp, argmax_br = bp, br
        tn, fp, fn, tp = self.binary_cm.ravel()
        bp = tp / (tp + fp) if tp + fp else 0.
        br = tp / (tp + fn) if tp + fn else 0.
        return {'rows': int(n), 'macro_f1': float(f1.mean()), 'weighted_f1': float((f1 * support).sum() / n),
                'balanced_accuracy': float(recall[support > 0].mean()), 'accuracy': float(cm.trace() / n),
                'class_4_precision': float(precision[4]), 'class_4_recall': float(recall[4]),
                'log_loss': self.loss / n, 'mean_absolute_class_error': float((cm * distance).sum() / n),
                'quadratic_weighted_kappa': float(1 - (cm * distance**2).sum() / denominator) if denominator else None,
                'severe_error_rate': float(cm[distance >= 2].sum() / n),
                'needs_collection_precision': float(bp), 'needs_collection_recall': float(br),
                'needs_collection_f1': float(2 * bp * br / (bp + br)) if bp + br else 0.,
                'needs_collection_threshold': self.threshold,
                'needs_collection_rule': 'five-class argmax >=3' if self.threshold is None else 'probability_class_3 + probability_class_4 >= threshold',
                'needs_collection_tn': int(tn), 'needs_collection_fp': int(fp), 'needs_collection_fn': int(fn), 'needs_collection_tp': int(tp),
                'argmax_needs_collection_precision': float(argmax_bp), 'argmax_needs_collection_recall': float(argmax_br),
                'argmax_needs_collection_f1': float(2 * argmax_bp * argmax_br / (argmax_bp + argmax_br)) if argmax_bp + argmax_br else 0.,
                'per_class': [{'class': c, 'precision': float(precision[c]), 'recall': float(recall[c]),
                               'f1': float(f1[c]), 'support': int(support[c])} for c in range(5)],
                'confusion_matrix': self.cm.tolist(), 'normalized_confusion_matrix': normalized.tolist()}


def prediction_frame(frame, probabilities, model, split, threshold=None):
    result = frame[[c for c in ['bin_id', 'site_id', 'date', 'fill_level', 'input_quality_flag'] if c in frame]].reset_index(drop=True).copy()
    probabilities = validate_probabilities(probabilities)
    result['predicted_fill_level'] = probabilities.argmax(axis=1).astype('int8')
    for index, name in enumerate(PROBABILITY_COLUMNS):
        result[name] = probabilities[:, index]
    result['needs_collection_probability'] = probabilities[:, 3:].sum(axis=1)
    result['needs_collection'] = (result.predicted_fill_level >= 3 if threshold is None else result.needs_collection_probability >= threshold).astype('int8')
    result['model_name'], result['split'] = model, split
    return result


def evaluate_partition(config, name, period_name, *, bundle=None, baseline=None, output_name=None, threshold=None):
    folder = output_path(config, 'evaluation', period_name)
    folder.mkdir(parents=True, exist_ok=True)
    output_name = output_name or name
    target = folder / f'{output_name}_predictions.parquet'
    temporary = target.with_suffix('.parquet.tmp')
    writer = None
    overall = Metrics(threshold)
    groups = defaultdict(lambda: Metrics(threshold))
    try:
        for frame in feature_batches(config, config['splits'][period_name]):
            if bundle is not None:
                probabilities = bundle.predict_proba(frame)
            else:
                counts, group_table = baseline
                probabilities = baseline_probabilities(frame, counts, config['seed'], group_table)[name]
            overall.add(frame.fill_level, probabilities)
            for c in ['date', 'waste_type', 'capacity_range', 'input_quality_flag']:
                for value, indexes in frame.groupby(c, observed=True, dropna=False).indices.items():
                    groups[c, str(value)].add(frame.fill_level.iloc[indexes], probabilities[indexes])
            result = prediction_frame(frame, probabilities, output_name, period_name, threshold)
            table = pa.Table.from_pandas(result, preserve_index=False)
            if writer is None:
                writer = pq.ParquetWriter(temporary, table.schema, compression='zstd')
            writer.write_table(table)
        if writer is None:
            raise ValueError('No evaluation observations')
        writer.close(); writer = None
        temporary.replace(target)
    finally:
        if writer is not None:
            writer.close()
    report = overall.report()
    write_json(folder / f'{output_name}_metrics.json', report)
    group_rows = []
    for (c, value), accumulator in groups.items():
        r = accumulator.report()
        group_rows.append({'group': c, 'value': value, **{k: v for k, v in r.items() if k not in ['per_class', 'confusion_matrix', 'normalized_confusion_matrix']}})
    pd.DataFrame(group_rows).to_csv(folder / f'{output_name}_error_groups.csv', index=False)
    pd.DataFrame(report['per_class']).to_csv(folder / f'{output_name}_per_class.csv', index=False)
    pd.DataFrame(report['confusion_matrix']).to_csv(folder / f'{output_name}_confusion.csv', index_label='observed_class')
    pd.DataFrame(report['normalized_confusion_matrix']).to_csv(folder / f'{output_name}_confusion_normalized.csv', index_label='observed_class')
    return report


def select_operational_threshold(y, probabilities):
    rows = []
    for threshold in np.round(np.linspace(.05, .95, 19), 2):
        accumulator = Metrics(float(threshold))
        accumulator.add(y, probabilities)
        report = accumulator.report()
        rows.append({k: report[k] for k in ['needs_collection_threshold', 'needs_collection_precision', 'needs_collection_recall', 'needs_collection_f1', 'needs_collection_tp', 'needs_collection_fp', 'needs_collection_fn', 'needs_collection_tn']})
    curve = pd.DataFrame(rows)
    best = min(rows, key=lambda r: (-r['needs_collection_f1'], abs(r['needs_collection_threshold'] - .5), r['needs_collection_threshold']))
    return best['needs_collection_threshold'], curve


def _parameters(config,name):
    best=read_json(output_path(config,'search','best_parameters.json'))[name]
    params=dict(best['parameters'])
    if name=='catboost': params['iterations']=best['refit_iterations']
    return params


def _fit(config,name,sample,stage_name):
    with PeakMemory() as memory:
        bundle=fit_model(name,_parameters(config,name),sample,config)
    if memory.peak_gib>config['search']['max_process_memory_gib']:
        raise MemoryError('Fit exceeded the approved process RSS limit')
    bundle.metadata.update(stage=stage_name,peak_rss_gib=memory.peak_gib,versions=versions(),source_provenance=config['_provenance'],configuration_sha256=object_digest(clean_config(config)))
    return bundle


def train(config,args):
    require_approval(config,args.approval_json)
    verify_cache(config)
    if output_path(config,'selection.json').exists():
        raise ValueError('Selection already frozen; do not rerun training in this run')
    sample=sample_features(config,config['splits']['train'],config['sampling']['final_rows'],name='selection_train')
    comparisons=[]; reports={}; thresholds={}
    for name in model_names(config):
        bundle=_fit(config,name,sample,'selection_fit')
        validation=config['_frames']['validation']
        probabilities=bundle.predict_proba(validation)
        threshold,curve=select_operational_threshold(validation.fill_level,probabilities)
        thresholds[name]=threshold
        folder=output_path(config,'evaluation','validation'); folder.mkdir(parents=True,exist_ok=True)
        curve.to_csv(folder/f'{name}_threshold_curve.csv',index=False)
        reports[name]=evaluate_partition(config,name,'validation',bundle=bundle,threshold=threshold)
        comparisons.append({'model':name,'split':'validation',**{k:v for k,v in reports[name].items() if k not in ['per_class','confusion_matrix','normalized_confusion_matrix']}})
        write_json(folder/f'{name}_fit.json',bundle.metadata)
        del bundle,probabilities; gc.collect()
    counts=sample.fill_level.astype(int).value_counts().to_dict()
    groups=group_baseline_table(config)
    for name in ['dummy_most_frequent','dummy_stratified','previous_rating','training_group_median']:
        report=evaluate_partition(config,name,'validation',baseline=(counts,groups),threshold=.5)
        comparisons.append({'model':name,'split':'validation',**{k:v for k,v in report.items() if k not in ['per_class','confusion_matrix','normalized_confusion_matrix']}})
    selected=max(model_names(config),key=lambda n:reports[n]['needs_collection_f1'])
    selection={'model':selected,'criterion':'August validation needs_collection_f1','validation_score':reports[selected]['needs_collection_f1'],
        'needs_collection_threshold':thresholds[selected],'model_thresholds':thresholds,'selection_period':config['splits']['validation'],
        'decision_rule':'probability argmax','configuration_sha256':object_digest(clean_config(config)),
        'test_period_reused':True,'calibration':'none','frozen_parameters':{n:_parameters(config,n) for n in model_names(config)}}
    write_json(output_path(config,'selection.json'),selection)
    logging.info('August winner frozen: %s; thresholds=%s',selected,thresholds)
    pd.DataFrame(comparisons).to_csv(output_path(config,'model_comparison.csv'),index=False)
    sample=sample_features(config,config['final_train'],config['sampling']['final_rows'],name='final_train')
    folder=output_path(config,'models'); folder.mkdir(parents=True,exist_ok=True)
    for name in model_names(config):
        bundle=_fit(config,name,sample,'final_fit')
        bundle.metadata.update(needs_collection_threshold=thresholds[name],selection=selection,fit_period=config['final_train'])
        if pd.Timestamp(bundle.metadata['train_end'])>=pd.Timestamp('2026-09-01'):
            raise ValueError('Final fit crossed the September cutoff')
        bundle.save(folder/f'{name}.joblib')
        reloaded=load_model(folder/f'{name}.joblib')
        if not np.allclose(bundle.predict_proba(sample.head(64)),reloaded.predict_proba(sample.head(64)),atol=1e-12):
            raise ValueError('Saved model probabilities changed after reload')
        bundle.metadata['reload_probabilities_verified']=True
        del reloaded
        bundle.save(folder/f'{name}.joblib'); write_json(folder/f'{name}.json',bundle.metadata)
        logging.info('Final fit %s completed: %s rows, %.1fs',name,len(sample),bundle.metadata['duration_seconds'])
        del bundle; gc.collect()
    shutil.copy2(folder/f'{selected}.joblib',folder/'selected.joblib')


def evaluate(config,args):
    verify_cache(config)
    if output_path(config,'test_evaluation_complete.json').exists():
        raise ValueError('Demo evaluation already complete')
    selection=read_json(output_path(config,'selection.json'))
    selection_hash=digest(output_path(config,'selection.json'))
    comparisons=pd.read_csv(output_path(config,'model_comparison.csv')).to_dict('records')
    sample=config['_frames']['final']; counts=sample.fill_level.astype(int).value_counts().to_dict()
    groups=group_baseline_table(config,final=True)
    for name in model_names(config)+['dummy_most_frequent','dummy_stratified','previous_rating','training_group_median']:
        bundle=load_model(output_path(config,'models',f'{name}.joblib')) if name in model_names(config) else None
        threshold=selection['model_thresholds'].get(name,.5)
        report=evaluate_partition(config,name,'test',bundle=bundle,baseline=(counts,groups),threshold=threshold)
        comparisons.append({'model':name,'split':'test',**{k:v for k,v in report.items() if k not in ['per_class','confusion_matrix','normalized_confusion_matrix']}})
        del bundle; gc.collect()
    pd.DataFrame(comparisons).to_csv(output_path(config,'model_comparison.csv'),index=False)
    if digest(output_path(config,'selection.json'))!=selection_hash: raise ValueError('Selection changed during evaluation')
    write_json(output_path(config,'test_evaluation_complete.json'),{'selection_sha256':selection_hash})


def predict(config,args):
    verify_cache(config)
    selection=read_json(output_path(config,'selection.json'))
    folder=output_path(config,'predictions'); folder.mkdir(parents=True,exist_ok=True)
    per_day=[]
    for name in model_names(config):
        bundle=load_model(output_path(config,'models',f'{name}.joblib'))
        threshold=selection['model_thresholds'][name]
        for day in pd.date_range(*config['splits']['test']):
            frame=registry_features(config,day)
            p=bundle.predict_proba(frame)
            result=prediction_frame(frame,p,name,'demo_next_day',threshold)
            result['today']=day-pd.Timedelta(days=1)
            result.to_csv(folder/f'{name}_{day:%Y-%m-%d}.csv',index=False)
            if len(result)!=config['expected']['registry_bins'] or result.bin_id.duplicated().any(): raise ValueError('Registry output coverage failed')
            labeled=frame.fill_level.notna().to_numpy()
            accumulator=Metrics(threshold); accumulator.add(frame.loc[labeled,'fill_level'],p[labeled])
            report=accumulator.report()
            per_day.append({'model':name,'today':str((day-pd.Timedelta(days=1)).date()),'forecast_date':str(day.date()),'registry_bins':len(result),
                **{k:v for k,v in report.items() if k not in ['per_class','confusion_matrix','normalized_confusion_matrix']}})
            if name==selection['model']:
                result[['bin_id','predicted_fill_level']].rename(columns={'predicted_fill_level':'fill_level'}).to_csv(folder/f'product_{day:%Y-%m-%d}.csv',index=False)
        del bundle; gc.collect()
        logging.info('All 30 registry forecasts complete: %s',name)
    table=pd.DataFrame(per_day); table.to_csv(folder/'daily_comparison.csv',index=False)
    control=table.loc[table.forecast_date==config['prediction_date']]
    control.to_csv(folder/f'model_control_comparison_{config["prediction_date"]}.csv',index=False)
    chosen=control.loc[control.model==selection['model']].iloc[0]
    quality=registry_features(config,config['prediction_date']).input_quality_flag.value_counts().to_dict()
    write_json(folder/f'coverage_{config["prediction_date"]}.json',{'date':config['prediction_date'],'registry_bins':int(chosen.registry_bins),
        'labeled_comparison':{k:v for k,v in chosen.to_dict().items() if k not in ['model','today','forecast_date']},
        'quality_distribution':quality,'comparison_is_synthetic':True,'demo_dates':30})

def unseen_sites(config, args):
    verify_cache(config)
    selection = read_json(output_path(config, 'selection.json'))
    sites = pd.read_csv(source_path(config, 'registry'), usecols=['site_id']).site_id.unique()
    rng = np.random.default_rng(config['seed'])
    holdout = rng.choice(np.sort(sites), size=max(1, int(len(sites) * config['unseen_sites']['fraction'])), replace=False)
    sample = sample_features(config, config['final_train'], config['sampling']['final_rows'], name='unseen_site_train', exclude_sites=holdout)
    if sample.site_id.isin(holdout).any():
        raise ValueError('Held-out sites entered training')
    metadata = read_json(output_path(config, 'models', f'{selection["model"]}.json'))
    with PeakMemory() as memory:
        bundle = fit_model(selection['model'], metadata['parameters'], sample, config)
    if memory.peak_gib > config['search']['max_process_memory_gib']:
        raise MemoryError('Unseen-site fit exceeded the confirmed memory budget')
    folder = output_path(config, 'unseen_sites')
    folder.mkdir(parents=True, exist_ok=True)
    bundle.metadata.update(peak_rss_gib=memory.peak_gib, held_out_sites=len(holdout), versions=versions())
    write_json(folder / 'model.json', bundle.metadata)
    pd.DataFrame({'site_id': holdout}).to_csv(folder / 'held_out_sites.csv', index=False)
    threshold = selection.get('needs_collection_threshold')
    accumulator = Metrics(threshold)
    evaluated_bins, evaluated_sites = set(), set()
    writer = None
    try:
        for frame in feature_batches(config, config['splits']['test']):
            frame = frame.loc[frame.site_id.isin(holdout)].copy()
            if not len(frame):
                continue
            evaluated_bins.update(frame.bin_id.unique().tolist())
            evaluated_sites.update(frame.site_id.unique().tolist())
            if config['unseen_sites']['cold_start']:
                frame[HISTORY] = np.nan
                frame['previous_collection_status'] = '__MISSING__'
                frame['history_label_count'] = 0
                frame['has_daily_history'] = False
                frame['input_quality_flag'] = quality_flags(frame)
            p = bundle.predict_proba(frame)
            accumulator.add(frame.fill_level, p)
            table = pa.Table.from_pandas(prediction_frame(frame, p, bundle.name, 'unseen_site_cold_start', threshold), preserve_index=False)
            if writer is None:
                writer = pq.ParquetWriter(folder / 'predictions.parquet', table.schema, compression='zstd')
            writer.write_table(table)
    finally:
        if writer is not None:
            writer.close()
    write_json(folder / 'metrics.json', {**accumulator.report(), 'held_out_sites': len(holdout),
                                         'cold_start': config['unseen_sites']['cold_start'], 'train_rows': len(sample),
                                         'evaluated_labeled_bins': len(evaluated_bins), 'evaluated_labeled_sites': len(evaluated_sites),
                                         'training_sites': int(sample.site_id.nunique()), 'seed': config['seed'],
                                         'test_period': config['splits']['test'], 'peak_fit_rss_gib': memory.peak_gib,
                                         'interpretation': 'Held-out labeled sites with unavailable history; unknown accuracy for truly unlabeled bins'})
