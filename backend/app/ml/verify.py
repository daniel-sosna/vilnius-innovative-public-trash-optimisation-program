"""Repeatable verification of the current experiment and developer delivery."""
import numpy as np
import pandas as pd
import logging
import time

from .common import (PROBABILITY_COLUMNS, digest, model_names, output_path,
                     read_json, source_path, write_json, run_cli)
from .features import FEATURES
from .evaluation import Metrics
from .modeling import load_model, validate_probabilities
from .package import verify_product
from .search import require_approval
from viptop_fill.csv_demo import predict_csv


def verify(config, args):
    root = output_path(config)
    checks = {}
    audit = read_json(root / 'validation/report.json')
    checks['source_audit'] = audit['passed']
    checks['source_hashes'] = all(digest(source_path(config, name)) == item['sha256']
                                 for name, item in audit['provenance']['inputs'].items())
    require_approval(config, root / 'approval.json')
    manifest = read_json(root / 'features_manifest.json')
    checks['active_schema'] = manifest['feature_columns'] == FEATURES and len(FEATURES) == 21
    checks['shared_builder_hash'] = manifest['provenance']['feature_code_sha256'] == digest(config['_root'] / 'backend/viptop_fill/features.py')
    checks['ephemeral_features'] = not any((root / p).exists() for p in ['features.parquet', 'registry_inputs'])
    sample_sizes = {'tuning': 20000, 'selection_train': 100000, 'final_train': 100000}
    for name, expected in sample_sizes.items():
        keys = pd.read_parquet(root / 'samples' / f'{name}_keys.parquet')
        metadata = read_json(root / 'samples' / f'{name}.json')
        period = config['final_train'] if name == 'final_train' else config['splits']['train']
        dates = pd.to_datetime(keys.date)
        checks[f'{name}_sample'] = (len(keys) == expected == metadata['sample_rows']
            and not keys.duplicated(['bin_id', 'date']).any()
            and set(keys.fill_level) == set(range(5))
            and dates.between(*map(pd.Timestamp, period)).all())
    fits = read_json(root / 'search/fits.json')
    checks['search_fits'] = len(fits) == 32 and len({(r['model'], r['phase'], r['candidate'], r['fold']) for r in fits}) == 32 and all(
        sum(r['model'] == model and r['phase'] == phase for r in fits) == 8
        for model in model_names(config) for phase in ['coarse', 'refined'])
    checks['search_boundaries'] = all(pd.Timestamp(r['train_period'][1]) < pd.Timestamp(r['validation_period'][0])
        <= pd.Timestamp(r['validation_period'][1]) < pd.Timestamp('2026-08-01') for r in fits)
    checks['search_resources'] = (read_json(root / 'search/complete.json')['duration_seconds'] <= config['search']['budget_seconds']
        and max(r['peak_rss_gib'] for r in fits) <= config['search']['max_process_memory_gib'])
    selection = read_json(root / 'selection.json')
    checks['selection_frozen'] = (read_json(root / 'test_evaluation_complete.json')['selection_sha256'] == digest(root / 'selection.json')
        and selection['selection_period'] == config['splits']['validation'])
    validation_scores = {}
    for name in model_names(config):
        metadata = read_json(root / 'models' / f'{name}.json')
        checks[f'{name}_final_fit'] = (metadata['features'] == FEATURES
            and metadata['train_rows'] == 100000 and metadata['stage'] == 'final_fit'
            and pd.Timestamp(metadata['train_end']) < pd.Timestamp('2026-09-01')
            and metadata['parameters'] == selection['frozen_parameters'][name]
            and metadata['needs_collection_threshold'] == selection['model_thresholds'][name]
            and metadata['reload_probabilities_verified']
            and metadata['peak_rss_gib'] <= config['search']['max_process_memory_gib'])
        load_model(root / 'models' / f'{name}.joblib')
        fit = read_json(root / 'evaluation/validation' / f'{name}_fit.json')
        checks[f'{name}_selection_fit'] = pd.Timestamp(fit['train_end']) < pd.Timestamp('2026-08-01')
        curve = pd.read_csv(root / 'evaluation/validation' / f'{name}_threshold_curve.csv')
        checks[f'{name}_threshold_grid'] = (len(curve) == 19 and np.allclose(curve.needs_collection_threshold, np.arange(.05, 1, .05)))
        validation_scores[name] = read_json(root / 'evaluation/validation' / f'{name}_metrics.json')['needs_collection_f1']
    checks['august_winner'] = selection['model'] == max(model_names(config), key=validation_scores.get)
    registry_ids = set(pd.read_csv(source_path(config, 'registry'), usecols=['id']).id)
    daily = pd.read_csv(root / 'predictions/daily_comparison.csv')
    checks['thirty_scenarios'] = len(daily) == 60 and not daily.duplicated(['model', 'forecast_date']).any()
    for name in model_names(config):
        pooled = Metrics(selection['model_thresholds'][name])
        for day in pd.date_range(*config['demo_today']):
            target = day + pd.Timedelta(days=1)
            table = pd.read_csv(root / 'predictions' / f'{name}_{target:%Y-%m-%d}.csv')
            p = validate_probabilities(table[PROBABILITY_COLUMNS].to_numpy())
            if len(table) != len(registry_ids) or table.bin_id.duplicated().any() or set(table.bin_id) != registry_ids:
                raise ValueError(f'Coverage failed: {name}/{target}')
            if not pd.to_datetime(table.date).eq(target).all() or not pd.to_datetime(table.today).eq(day).all():
                raise ValueError('Invalid today/forecast mapping')
            if not np.array_equal(p.argmax(axis=1), table.predicted_fill_level):
                raise ValueError('Product class mapping mismatch')
            labels = table.fill_level.notna()
            pooled.add(table.loc[labels, 'fill_level'], p[labels])
            metric = daily.loc[(daily.model == name) & (daily.forecast_date == str(target.date()))].iloc[0]
            if int(metric.rows) != int(labels.sum()):
                raise ValueError('Daily labeled denominator mismatch')
            if name == selection['model']:
                product = pd.read_csv(root / 'predictions' / f'product_{target:%Y-%m-%d}.csv')
                expected = table[['bin_id', 'predicted_fill_level']].rename(columns={'predicted_fill_level': 'fill_level'})
                if list(product) != ['bin_id', 'fill_level'] or not product.equals(expected):
                    raise ValueError('Two-column export differs from the selected model')
        stored = read_json(root / 'evaluation/test' / f'{name}_metrics.json')
        computed = pooled.report()
        checks[f'{name}_pooled_metrics'] = all(np.isclose(computed[k], stored[k]) for k in
            ['rows', 'macro_f1', 'needs_collection_f1', 'argmax_needs_collection_f1', 'mean_absolute_class_error'])
    charts = pd.read_csv(root / 'chart_sources.csv')
    checks['chart_sources'] = len(charts) > 0 and all((root / row.chart).is_file() and (root / row.source_table).is_file()
        for row in charts.itertuples()) and set(charts.chart) == {p.relative_to(root).as_posix() for p in (root / 'charts').rglob('*.png')}
    holdout = set(pd.read_csv(root / 'unseen_sites/held_out_sites.csv').site_id)
    cold_keys = pd.read_parquet(root / 'samples/unseen_site_train_keys.parquet')
    checks['unseen_sites_disjoint'] = (not cold_keys.site_id.isin(holdout).any() and len(cold_keys) == 100000
        and pd.to_datetime(cold_keys.date).between(*map(pd.Timestamp, config['final_train'])).all())
    cold_predictions = pd.read_parquet(root / 'unseen_sites/predictions.parquet', columns=['site_id', 'input_quality_flag'])
    checks['cold_start_mask'] = (cold_predictions.site_id.isin(holdout).all() and all(
        cold_predictions.input_quality_flag.str.contains(flag, regex=False).all()
        for flag in ['no_daily_history', 'no_historical_labels', 'missing_qr_history']))
    for name in model_names(config):
        native = pd.read_csv(root / 'importance' / f'{name}_native.csv')
        permutation = pd.read_csv(root / 'importance' / f'{name}_permutation.csv')
        checks[f'{name}_importance_schema'] = set(native.feature) == set(FEATURES) == set(permutation.feature)
    importance_keys = pd.read_parquet(root / 'samples/importance_demo_keys.parquet')
    checks['importance_dates'] = (len(importance_keys) == 500 and
        pd.to_datetime(importance_keys.date).between(*map(pd.Timestamp, config['splits']['test'])).all())
    checks['report'] = (root / 'README_REPORT.md').is_file()
    verify_product(config)
    checks['isolated_product'] = read_json(root / 'product_verification.json')['passed']
    csv_check_path = root / 'csv_registry_verification.json'
    model_hash = digest(root / 'product/manifest.json')
    source_hash = audit['provenance']['inputs']['daily']['sha256']
    previous = read_json(csv_check_path) if csv_check_path.exists() else {}
    if previous.get('manifest_sha256') != model_hash or previous.get('source_sha256') != source_hash:
        logging.info('Full portable CSV verification started: all registry bins, today 2026-09-15')
        started = time.monotonic()
        read = lambda name: pd.read_csv(source_path(config, name), keep_default_na=False, na_values=['', 'NULL'])
        predicted = predict_csv(root / 'product', source_path(config, 'daily'), read('registry'), '2026-09-15', read('population'))
        expected = pd.read_csv(root / 'predictions/product_2026-09-16.csv')
        pd.testing.assert_frame_equal(predicted.sort_values('bin_id').reset_index(drop=True),
                                      expected.sort_values('bin_id').reset_index(drop=True), check_dtype=False)
        previous = {'passed': True, 'rows': len(predicted), 'today': '2026-09-15', 'forecast_date': '2026-09-16',
                    'manifest_sha256': model_hash, 'source_sha256': source_hash, 'duration_seconds': time.monotonic() - started}
        write_json(csv_check_path, previous)
        logging.info('Full portable CSV equality verified: %s bins in %.1fs', len(predicted), previous['duration_seconds'])
    checks['full_registry_product'] = previous.get('passed') is True and previous.get('rows') == len(registry_ids)
    failed = [name for name, passed in checks.items() if not passed]
    write_json(root / 'delivery_verification.json', {'passed': not failed, 'checks': {k: bool(v) for k, v in checks.items()}, 'failed': failed})
    if failed:
        raise ValueError('Delivery checks failed: ' + ', '.join(failed))
    from .reporting import verification_summary
    verification_summary(config)
    print(f'Current delivery verified: {len(checks)} checks, 30 next-day dates, both final models, isolated product.')


if __name__ == '__main__':
    run_cli('Verify the current September experiment and isolated product.', verify)
