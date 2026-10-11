"""Training-only sampling, fold-fitted preprocessing and reloadable probability models."""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
import time

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer, MissingIndicator
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.metrics import f1_score

from .common import output_path, split_mask, write_json
from .features import CATEGORICAL, FEATURES, NUMERIC


def seeded_keys(frame, seed):
    salt = np.uint64((int(seed) * 0x9E3779B97F4A7C15) % (1 << 64))
    return pd.util.hash_pandas_object(frame[['bin_id', 'date']], index=False).to_numpy() ^ salt


def feature_batches(config, period, *, columns=None):
    from .features import build_features
    build_features(config)
    frames = config['_frames']
    key = next((name for name in ['validation','test','train'] if list(period) == config['splits'][name]), None)
    key = key or ('final' if list(period) == config['final_train'] else 'train')
    source = frames[key]
    for start in range(0,len(source),100000):
        frame = source.iloc[start:start+100000]
        frame = frame.loc[split_mask(frame,period)]
        if len(frame):
            yield frame.copy() if columns is None else frame[columns].copy()


def sample_features(config, period, limit, *, name, stratified=True, exclude_sites=None):
    """Bottom-key hash sample plus one representative per observed training stratum."""
    candidate = None
    mandatory = {}
    total = 0
    strata = ['date', 'fill_level', 'waste_type', 'object_group']
    schemas = ([['date', 'fill_level'], ['waste_type', 'object_group', 'fill_level']]
               if config['sampling'].get('strata') == 'marginal' else [strata])
    for frame in (feature_batches(config, period) if exclude_sites is None else [config['_frames']['cold']]):
        if exclude_sites is not None:
            frame = frame.loc[~frame.site_id.isin(exclude_sites)].copy()
        total += len(frame)
        frame['_priority'] = seeded_keys(frame, config['seed'])
        candidate = frame if candidate is None else pd.concat([candidate, frame], ignore_index=True)
        candidate = candidate.nsmallest(limit, '_priority').copy()
        if stratified:
            for index, schema in enumerate(schemas):
                best = frame.loc[frame.groupby(schema, observed=True, dropna=False)['_priority'].idxmin()]
                merged = best if index not in mandatory else pd.concat([mandatory[index], best], ignore_index=True)
                mandatory[index] = merged.loc[merged.groupby(schema, observed=True, dropna=False)['_priority'].idxmin()].copy()
    if candidate is None or candidate.empty:
        raise ValueError(f'No labeled sample rows in {period}')
    strata_counts = {','.join(schemas[k]): len(v) for k, v in mandatory.items()}
    mandatory = pd.concat(list(mandatory.values()), ignore_index=True).drop_duplicates(['bin_id', 'date']) if mandatory else None
    if mandatory is not None:
        if len(mandatory) > limit:
            raise ValueError(f'{name}: {len(mandatory)} observed date/class/waste/object strata exceed sample limit {limit}; increase it explicitly')
        mandatory_index = pd.MultiIndex.from_frame(mandatory[['bin_id', 'date']])
        other = candidate.loc[~pd.MultiIndex.from_frame(candidate[['bin_id', 'date']]).isin(mandatory_index)]
        candidate = pd.concat([mandatory, other.nsmallest(limit - len(mandatory), '_priority')], ignore_index=True)
    result = candidate.drop(columns='_priority').sort_values(['date', 'bin_id']).reset_index(drop=True)
    if set(result.fill_level.unique()) != set(range(5)):
        raise ValueError(f'{name}: sample lacks a target class; increase the sample explicitly')
    folder = output_path(config, 'samples')
    folder.mkdir(parents=True, exist_ok=True)
    result[['bin_id', 'site_id', 'date', 'fill_level']].to_parquet(folder / f'{name}_keys.parquet', index=False)
    write_json(folder / f'{name}.json', {'method': 'seeded bottom hash of bin/date; mandatory minimum hash per observed stratum in each recorded schema' if stratified else 'seeded bottom hash of bin/date',
                                        'strata_counts': strata_counts,
                                        'period': period, 'seed': config['seed'], 'eligible_rows': config.get('_eligible', {}).get('cold' if exclude_sites is not None else 'final' if list(period) == config.get('final_train') else 'train', total) if list(period) in [config['splits']['train'], config.get('final_train')] else total,
                                        'sample_rows': len(result), 'observed_strata': len(mandatory) if mandatory is not None else None,
                                        'dates': int(result.date.nunique()), 'bins': int(result.bin_id.nunique()),
                                        'sites': int(result.site_id.nunique()), 'classes': result.fill_level.value_counts().to_dict(),
                                        'waste_types': sorted(result.waste_type.unique().tolist()),
                                        'object_groups': sorted(result.object_group.unique().tolist())})
    return result


def selected_features(config):
    return list(FEATURES)


def score_predictions(config, y, probabilities, threshold=.5):
    if config.get('objective') == 'needs_collection_f1':
        return f1_score(np.asarray(y) >= 3, probabilities[:, 3:].sum(axis=1) >= threshold, zero_division=0)
    return f1_score(y, probabilities.argmax(axis=1), average='macro', zero_division=0)


from viptop_fill.runtime import model_input, catboost_input, validate_probabilities


@dataclass
class ModelBundle:
    name: str
    preprocessing: object
    model: object
    metadata: dict

    def predict_proba(self, frame):
        x = model_input(frame, self.metadata['features'])
        if self.name == 'catboost':
            x = catboost_input(frame, self.preprocessing, features=self.metadata['features'])
            raw = self.model.predict_proba(x)
        else:
            raw = self.model.predict_proba(self.preprocessing.transform(x))
        result = np.zeros((len(frame), 5), dtype=float)
        for index, label in enumerate(self.model.classes_):
            label = int(label)
            if label not in range(5):
                raise ValueError('Model contains an unexpected target class')
            result[:, label] = raw[:, index]
        return validate_probabilities(result)

    def save(self, path):
        joblib.dump(self, path, compress=3)

    def predict_needs_collection(self, frame):
        p = self.predict_proba(frame)
        threshold = self.metadata.get('needs_collection_threshold')
        return (p.argmax(axis=1) >= 3 if threshold is None else p[:, 3:].sum(axis=1) >= threshold).astype('int8')


def load_model(path):
    """Load only locally trusted artifacts produced by this pipeline."""
    bundle = joblib.load(path)
    if (not isinstance(bundle, ModelBundle) or not bundle.metadata['features']
            or len(set(bundle.metadata['features'])) != len(bundle.metadata['features'])
            or any(c not in FEATURES for c in bundle.metadata['features'])):
        raise ValueError('Incompatible model artifact')
    return bundle


def fit_model(name, parameters, train, config, *, evaluation=None, pilot=False):
    y = train.fill_level.to_numpy(dtype=int)
    if set(np.unique(y)) != set(range(5)):
        raise ValueError('Training fold lacks one or more target classes; revise the training-only sample/fold')
    features = selected_features(config)
    numeric = [c for c in NUMERIC if c in features]
    categorical = [c for c in CATEGORICAL if c in features]
    x = model_input(train, features)
    params = dict(parameters)
    if name == 'catboost':
        from catboost import CatBoostClassifier
    start = time.monotonic()
    seed, threads = config['seed'], config['threads']
    if name == 'catboost':
        from catboost import CatBoostClassifier
        prep = SimpleImputer(strategy='median', keep_empty_features=True)
        x = catboost_input(train, prep, fit=True, features=features)
        if params.get('auto_class_weights') is None:
            params.pop('auto_class_weights', None)
        model = CatBoostClassifier(**params, loss_function='MultiClass', random_seed=seed,
                                   thread_count=threads, cat_features=categorical,
                                   bootstrap_type='Bayesian', task_type='GPU' if config['search']['device'].startswith('cuda') else 'CPU',
                                   **({'gpu_ram_part': config['search'].get('gpu_ram_part', .5), 'devices': '0'} if config['search']['device'].startswith('cuda') else {}), allow_writing_files=False,
                                   verbose=False)
        fit_args = {}
        if evaluation is not None:
            ex = catboost_input(evaluation, prep, features=features)
            fit_args = {'eval_set': (ex, evaluation.fill_level.astype(int)), 'early_stopping_rounds': 35}
        model.fit(x, y, **fit_args)
    else:
        prep = ColumnTransformer([
            ('numeric', SimpleImputer(strategy='median', keep_empty_features=True), numeric),
            ('missing', MissingIndicator(features='all'), numeric),
            ('categorical', OneHotEncoder(handle_unknown='ignore', min_frequency=5,
                                          sparse_output=True, dtype=np.float32), categorical)], sparse_threshold=1.0)
        transformed = prep.fit_transform(x)
        if name == 'random_forest':
            model = RandomForestClassifier(**params, n_jobs=threads, random_state=seed)
            model.fit(transformed, y)
        else:
            raise ValueError(f'Unknown model {name}')
    iterations = int(model.tree_count_) if name == 'catboost' else int(parameters['n_estimators'])
    metadata = {'features': features, 'parameters': parameters, 'effective_iterations': iterations,
                'train_start': str(train.date.min().date()), 'train_end': str(train.date.max().date()),
                'train_rows': len(train), 'train_bins': int(train.bin_id.nunique()),
                'duration_seconds': time.monotonic() - start, 'seed': seed, 'pilot': pilot,
                'device': 'cpu' if name == 'random_forest' else config['search']['device'],
                'inference_device': 'cpu',
                'decision_rule': 'probability argmax', 'target': 'synthetic worker rating 0..4',
                'calibration': 'none'}
    bundle = ModelBundle(name, prep, model, metadata)
    bundle.predict_proba(train.iloc[:10])
    return bundle


def grid_candidates(grid):
    names = list(grid)
    return [dict(zip(names, values)) for values in product(*(grid[name] for name in names))]


def refined_grid(name, best):
    grid = {k: [v] for k, v in best.items()}
    if name == 'random_forest':
        grid.update(max_depth=[max(2, best['max_depth'] - 2), best['max_depth'] + 2], max_features=['sqrt', .7])
    else:
        grid.update(l2_leaf_reg=[3., 8.], random_strength=[.5, 1.5])
    return grid


def group_baseline_table(config, final=False):
    source = config['_frames']['final' if final else 'train']
    keys = ['waste_type','capacity_range','object_group']
    return source.groupby(keys,observed=True,dropna=False).fill_level.median().rename('group_median').reset_index()


def prior_ordinal_class(values):
    return np.floor(np.asarray(values) + .5)


def baseline_probabilities(frame, counts, seed, group_table):
    prior = np.array([counts.get(c,0) for c in range(5)],dtype=float)
    prior /= prior.sum()
    majority = int(prior.argmax())
    uniform = (seeded_keys(frame,seed) >> np.uint64(11)).astype(float)/2**53
    output = {'dummy_most_frequent': np.eye(5)[np.full(len(frame),majority)],
              'dummy_stratified': np.eye(5)[np.searchsorted(np.cumsum(prior),uniform).clip(0,4)]}
    merged = frame[['waste_type','capacity_range','object_group']].merge(group_table,on=['waste_type','capacity_range','object_group'],how='left',validate='many_to_one')
    for name,values in [('previous_rating',frame.previous_worker_rating),('training_group_median',merged.group_median)]:
        predicted=prior_ordinal_class(values)
        output[name]=np.eye(5)[np.where(np.isfinite(predicted),predicted,majority).astype(int)]
    return output
