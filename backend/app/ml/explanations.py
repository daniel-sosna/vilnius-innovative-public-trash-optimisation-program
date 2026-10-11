"""Descriptive importance in original variables and bounded held-out SHAP."""
from collections import Counter
import logging
import time

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score

from .common import model_names, output_path, read_json, write_json
from .features import FEATURES, NUMERIC, verify_cache
from .modeling import catboost_input, load_model, model_input, sample_features, selected_features, score_predictions
from .search import PeakMemory


def original_name(transformed):
    name = transformed.split('__', 1)[-1]
    name = name.removeprefix('missingindicator_')
    for original in sorted(FEATURES, key=len, reverse=True):
        if name == original or name.startswith(original + '_'):
            return original
    raise ValueError(f'Cannot map transformed feature: {transformed}')


def aggregate_importance(names, values):
    total = Counter()
    for name, value in zip(names, values):
        total[original_name(name)] += float(value)
    return pd.DataFrame([{'feature': c, 'importance': v} for c, v in total.most_common()])


def explain(config, args):
    verify_cache(config)
    sample = sample_features(config, config['splits']['test'], config['sampling']['permutation_rows'],
                             name='importance_demo', stratified=False)
    folder = output_path(config, 'importance')
    folder.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(config['seed'])
    active_numeric = [c for c in NUMERIC if c in selected_features(config)]
    numeric = sample[active_numeric].corr()
    correlated = [{'feature_a': a, 'feature_b': b, 'correlation': float(numeric.loc[a, b])}
                  for i, a in enumerate(active_numeric) for b in active_numeric[i + 1:]
                  if pd.notna(numeric.loc[a, b]) and abs(numeric.loc[a, b]) >= .8]
    pd.DataFrame(correlated, columns=['feature_a', 'feature_b', 'correlation']).to_csv(folder / 'correlated_features.csv', index=False)
    diagnostics = {}
    for name in model_names(config):
        bundle = load_model(output_path(config, 'models', f'{name}.joblib'))
        if name == 'catboost':
            names = bundle.model.feature_names_
            values = bundle.model.feature_importances_
        else:
            names = bundle.preprocessing.get_feature_names_out()
            values = bundle.model.feature_importances_
        aggregate_importance(names, values).to_csv(folder / f'{name}_native.csv', index=False)
        threshold = bundle.metadata.get('needs_collection_threshold', .5)
        baseline = score_predictions(config, sample.fill_level, bundle.predict_proba(sample), threshold)
        rows = []
        for feature in bundle.metadata['features']:
            scores = []
            for repetition in range(3):
                permuted = sample.copy()
                permuted[feature] = rng.permutation(permuted[feature].to_numpy())
                scores.append(baseline - score_predictions(config, permuted.fill_level, bundle.predict_proba(permuted), threshold))
            rows.append({'feature': feature, 'importance': float(np.mean(scores)), 'std': float(np.std(scores))})
        pd.DataFrame(rows).sort_values('importance', ascending=False).to_csv(folder / f'{name}_permutation.csv', index=False)
        examples = sample.iloc[:config['sampling']['shap_rows']].copy()
        started = time.monotonic()
        try:
            with PeakMemory() as memory:
                if name == 'catboost':
                    from catboost import Pool
                    x = catboost_input(examples, bundle.preprocessing, features=bundle.metadata['features'])
                    raw = bundle.model.get_feature_importance(Pool(x, cat_features=bundle.model.get_cat_feature_indices()), type='ShapValues')
                    # CatBoost: observations x classes x (features + expected value).
                    values = np.transpose(raw[:, :, :-1], (0, 2, 1))
                    names = x.columns
                else:
                    import shap
                    x = bundle.preprocessing.transform(model_input(examples, bundle.metadata['features']))
                    x = x.toarray() if hasattr(x, 'toarray') else x
                    values = np.asarray(shap.TreeExplainer(bundle.model).shap_values(x))
                    names = bundle.preprocessing.get_feature_names_out()
                if values.shape != (len(examples), len(names), 5) or not np.isfinite(values).all():
                    raise ValueError(f'Unexpected SHAP result shape {values.shape}')
                aggregate_importance(names, np.abs(values).mean(axis=(0, 2))).to_csv(folder / f'{name}_shap_global.csv', index=False)
                for target_class in range(5):
                    aggregate_importance(names, np.abs(values[:, :, target_class]).mean(axis=0)).to_csv(folder / f'{name}_shap_class_{target_class}.csv', index=False)
                explanation_rows = []
                for index, (_, row) in enumerate(examples.iterrows()):
                    aggregated = Counter()
                    for feature, value in zip(names, values[index, :, 4]):
                        aggregated[original_name(feature)] += float(value)
                    for feature, value in sorted(aggregated.items(), key=lambda item: abs(item[1]), reverse=True)[:8]:
                        explanation_rows.append({'bin_id': row.bin_id, 'date': row.date, 'fill_level': row.fill_level,
                                                 'feature': feature, 'class_4_shap': value})
                pd.DataFrame(explanation_rows).to_csv(folder / f'{name}_class_4_examples.csv', index=False)
            diagnostics[name] = {'shap': 'completed', 'rows': len(examples), 'duration_seconds': time.monotonic() - started,
                                 'peak_rss_gib': memory.peak_gib, 'interpretation': 'Model contribution, not a causal effect; correlated variables can share importance'}
        except (MemoryError, ImportError, ValueError, RuntimeError, AttributeError) as error:
            diagnostics[name] = {'shap': 'unavailable', 'duration_seconds': time.monotonic() - started,
                                 'reason': f'{type(error).__name__}: {error}'}
            logging.warning('SHAP %s: %s', name, error)
    write_json(folder / 'diagnostics.json', diagnostics)
    selected = read_json(output_path(config, 'selection.json'))['model']
    top = pd.read_csv(folder / f'{selected}_permutation.csv').head(5).feature.tolist()
    (folder / 'presentation_explanation.md').write_text(
        f'# Synthetic fill prediction explanation\n\nSelected model: {selected}. '
        f'Largest held-out permutation effects: {", ".join(top)}. '
        'The model combines static container attributes with signals known before the prediction day. '
        'Past collection, retained worker ratings and QR signals can indicate accumulated demand; importance does not establish causality. '
        'Correlated variables share predictive information. Synthetic collection-day performance does not establish real-world or unlabeled-day accuracy.\n', encoding='utf-8')
