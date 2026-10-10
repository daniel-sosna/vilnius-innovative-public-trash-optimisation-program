"""Full-file streaming data audit and concise EDA with source tables."""
from collections import Counter, defaultdict
import logging

import numpy as np
import pandas as pd

from .common import (HEADER, STATUSES, SUCCESS, daily_chunks, digest, output_path,
                     provenance, require_sources, source_path, split_mask, versions, write_json)
from .features import capacity_range


def dictionary(frame):
    return [{'column': c, 'dtype': str(frame[c].dtype), 'cardinality': int(frame[c].nunique()),
             'missing': int(frame[c].isna().sum()), 'missing_pct': float(frame[c].isna().mean() * 100),
             'examples': str(frame[c].dropna().unique()[:3].tolist())} for c in frame]


def summarize_coverage(config):
    """Derive registry exclusions and category drift from the audited source tables."""
    from .common import read_json
    from .features import aliases, contradictory_sites
    folder = output_path(config, 'validation')
    registry = pd.read_csv(source_path(config, 'registry'), keep_default_na=False, na_values=['', 'NULL'])
    labels = pd.read_csv(folder / 'labels_per_bin.csv')
    coverage = registry.rename(columns={'id': 'bin_id'}).merge(labels, on='bin_id', how='left', validate='one_to_one')
    coverage['has_daily_history'] = coverage.rows.notna()
    coverage['labeled_rows'] = coverage.labeled_rows.fillna(0).astype(int)
    mapping = aliases(config)
    canonical = coverage.sub_district.astype('string').str.strip().str.replace(r'\s+', ' ', regex=True).map(mapping)
    coverage['canonical_district'] = canonical.fillna('__AMBIGUOUS__')
    coverage['missing_object_group'] = coverage.object_group.isna()
    coverage['ambiguous_district'] = canonical.isna()
    coverage['invalid_capacity'] = coverage.capacity_m3.isna() | (coverage.capacity_m3 <= 0)
    coverage['contradictory_site_districts'] = coverage.site_id.isin(contradictory_sites(config, mapping))
    coverage.to_csv(folder / 'registry_label_coverage.csv', index=False)
    coverage.loc[coverage.labeled_rows == 0].to_csv(folder / 'bins_without_labels.csv', index=False)
    drift = pd.read_csv(folder / 'feature_distribution_by_split.csv', dtype={'value': str}, keep_default_na=False)
    records = []
    for feature, values in drift.groupby('feature'):
        train = set(values.loc[values.split == 'train', 'value'])
        for split, part in values.groupby('split'):
            unseen = part.loc[~part.value.isin(train)]
            records.append({'split': split, 'feature': feature, 'distinct_values': len(part),
                            'unseen_values_vs_train': len(unseen), 'rows_with_unseen_value': int(unseen.rows.sum())})
    pd.DataFrame(records).to_csv(folder / 'category_drift.csv', index=False)
    summary = {'registry_bins_without_labels': int(coverage.labeled_rows.eq(0).sum()),
               'registry_sites': int(coverage.site_id.nunique()),
               'registry_only_bins': int((~coverage.has_daily_history).sum()),
               'quality_issue_counts_nonexclusive': {c: int(coverage[c].sum()) for c in ['missing_object_group', 'ambiguous_district', 'invalid_capacity', 'contradictory_site_districts']}}
    generator_manifest = source_path(config, 'daily').parent / 'validation/fill_qr/manifest.json'
    if generator_manifest.exists():
        manifest = read_json(generator_manifest)
        summary['generator_manifest_sha256'] = digest(generator_manifest)
        summary['generator_exclusion_reason_counts_nonexclusive'] = manifest.get('exclusion_reason_counts')
        summary['generator_calibration'] = manifest.get('calibration')
        summary['generator_output_matches_audit'] = manifest.get('output', {}).get('sha256') == read_json(folder / 'report.json')['provenance']['inputs']['daily']['sha256']
    write_json(folder / 'coverage_summary.json', summary)


def validate_data(config, args):
    require_sources(config)
    folder = output_path(config, 'validation')
    folder.mkdir(parents=True, exist_ok=True)
    registry = pd.read_csv(source_path(config, 'registry'), dtype={'postal_code': 'string', 'house_number': 'string'},
                           keep_default_na=False, na_values=['', 'NULL'])
    required = {'id', 'site_id', 'waste_type', 'capacity_m3', 'sub_district', 'object_group'}
    if not required.issubset(registry) or registry.id.isna().any() or registry.id.duplicated().any():
        raise ValueError('Registry schema, missing IDs or duplicate IDs are invalid')
    pd.DataFrame(dictionary(registry)).to_csv(folder / 'registry_dictionary.csv', index=False)
    if source_path(config, 'population').exists():
        population = pd.read_csv(source_path(config, 'population'), keep_default_na=False, na_values=['', 'NULL'])
        if not {'bin_id', 'population_cell_id', 'resident_factor'}.issubset(population) or population.bin_id.duplicated().any():
            raise ValueError('Invalid population snapshot schema or duplicate IDs')
        pd.DataFrame(dictionary(population)).to_csv(folder / 'population_dictionary.csv', index=False)
    missing, distinct, examples, dtypes = Counter(), defaultdict(set), {}, {}
    bins, bin_labels, site_labels = Counter(), Counter(), Counter()
    first, last, attrs = {}, {}, {}
    checks, labels, statuses = Counter(), Counter(), Counter()
    distributions = defaultdict(Counter)
    drift = defaultdict(Counter)
    previous = None
    rows = 0
    split = {name: {'rows': 0, 'labeled_rows': 0, 'classes': Counter(), 'missing': Counter(),
                    'bins': set(), 'sites': set(), 'labeled_bins': set(), 'labeled_sites': set()}
             for name in config['splits']}
    for chunk_index, frame in enumerate(daily_chunks(config)):
        rows += len(frame)
        for c in HEADER:
            missing[c] += int(frame[c].isna().sum())
            distinct[c].update(frame[c].dropna().unique())
            examples.setdefault(c, str(frame[c].dropna().unique()[:3].tolist()))
            dtypes.setdefault(c, str(frame[c].dtype))
        current_labels = frame.fill_level.dropna()
        labels.update(current_labels.value_counts().to_dict())
        statuses.update(frame.collection_status.value_counts().to_dict())
        bins.update(frame.bin_id.value_counts().to_dict())
        bin_labels.update(frame.loc[frame.fill_level.notna(), 'bin_id'].value_counts().to_dict())
        site_labels.update(frame.loc[frame.fill_level.notna(), 'site_id'].value_counts().to_dict())
        bid = frame.bin_id.to_numpy()
        days = frame.date.to_numpy(dtype='datetime64[D]').astype('int64')
        db, dd = np.diff(bid), np.diff(days)
        checks['unordered_bins'] += int((db < 0).sum())
        checks['date_gaps_or_unordered'] += int(((db == 0) & (dd != 1)).sum())
        checks['duplicate_keys'] += int(((db == 0) & (dd == 0)).sum())
        if previous:
            checks['unordered_bins'] += int(bid[0] < previous[0])
            checks['date_gaps_or_unordered'] += int(bid[0] == previous[0] and days[0] - previous[1] != 1)
            checks['duplicate_keys'] += int(bid[0] == previous[0] and days[0] == previous[1])
        previous = (bid[-1], days[-1])
        grouped = frame.groupby('bin_id', sort=False)
        for b, value in grouped.date.first().items():
            first.setdefault(int(b), value)
        last.update(grouped.date.last().to_dict())
        static_columns = ['site_id', 'waste_type', 'capacity_m3', 'sub_district', 'object_group', 'population_cell_id', 'resident_factor']
        for b, values in grouped[static_columns].first().iterrows():
            record = tuple(None if pd.isna(v) else v for v in values)
            if b in attrs and attrs[b] != record:
                checks['static_changes'] += 1
            attrs[b] = record
        checks['invalid_targets'] += int((frame.fill_level.notna() & ~frame.fill_level.isin(range(5))).sum())
        checks['labels_on_unsuccessful_days'] += int((frame.fill_level.notna() & ~frame.collection_status.isin(SUCCESS)).sum())
        checks['unknown_statuses'] += int((~frame.collection_status.isin(STATUSES)).sum())
        checks['infinite_numeric'] += int(np.isinf(frame.select_dtypes(include='number').to_numpy()).sum())
        checks['negative_exposure'] += int((frame.resident_factor < 0).sum())
        checks['negative_qr'] += int((frame.qr_alerts < 0).sum())
        checks['noninteger_qr'] += int((frame.qr_alerts.dropna() % 1 != 0).sum())
        checks['negative_holidays'] += int((frame.holidays_since_last_collection < 0).sum())
        for c in ['collections_last_28d', 'missed_collections_28d']:
            checks[c + '_invalid'] += int(((frame[c] < 0) | (frame[c] > 28) | (frame[c] % 1 != 0)).sum())
        checks['counter_sum_over_28'] += int(((frame.collections_last_28d + frame.missed_collections_28d) > 28).sum())
        checks['invalid_calendar'] += int(((frame.day_of_week != frame.date.dt.isocalendar().day) |
                                           (frame.week_of_year != frame.date.dt.isocalendar().week) |
                                           (frame.month != frame.date.dt.month) |
                                           (frame.season != (frame.date.dt.month % 12) // 3 + 1)).sum())
        for name, period in config['splits'].items():
            part = frame.loc[split_mask(frame, period)]
            item = split[name]
            item['rows'] += len(part)
            labeled_part = part.loc[part.fill_level.notna()]
            item['labeled_rows'] += len(labeled_part)
            item['classes'].update(labeled_part.fill_level.value_counts().to_dict())
            item['missing'].update(part.isna().sum().to_dict())
            item['bins'].update(part.bin_id.unique())
            item['sites'].update(part.site_id.unique())
            item['labeled_bins'].update(labeled_part.bin_id.unique())
            item['labeled_sites'].update(labeled_part.site_id.unique())
            for c in ['waste_type', 'capacity_m3', 'sub_district', 'object_group', 'resident_factor',
                      'qr_alerts', 'collections_last_28d', 'missed_collections_28d']:
                drift[name, c].update(part[c].fillna('__MISSING__').value_counts().to_dict())
        eda = frame[['date', 'waste_type', 'capacity_m3', 'sub_district', 'object_group', 'fill_level', 'qr_alerts', 'collection_status']].copy()
        eda['capacity_range'] = capacity_range(eda.capacity_m3)
        eda['qr_range'] = pd.cut(eda.qr_alerts, [-np.inf, 0, 1, 5, 20, 100, np.inf],
                                 labels=['zero', 'one', '2-5', '6-20', '21-100', '101+']).astype('string').fillna('missing')
        eda['target'] = eda.fill_level.fillna(-1).astype(int)
        for c in ['date', 'waste_type', 'capacity_range', 'sub_district', 'object_group', 'qr_range']:
            table = eda.groupby([c, 'target'], observed=True, dropna=False).size()
            distributions[c].update({(str(k[0]), int(k[1])): int(v) for k, v in table.items()})
        if chunk_index % 30 == 0:
            logging.info('Validation: rows=%s', rows)
    expected = config['expected']
    checks['wrong_total_rows'] = int(rows != expected['rows'])
    checks['wrong_daily_bin_count'] = int(len(bins) != expected['daily_bins'])
    checks['wrong_registry_count'] = int(len(registry) != expected['registry_bins'])
    checks['outside_registry'] = len(set(bins) - set(registry.id))
    checks['incomplete_bin_ranges'] = sum(first[b] != pd.Timestamp(expected['start']) or last[b] != pd.Timestamp(expected['end']) for b in bins)
    checks['wrong_rows_per_bin'] = sum(v != (pd.Timestamp(expected['end']) - pd.Timestamp(expected['start'])).days + 1 for v in bins.values())
    mismatch = {}
    indexed = registry.set_index('id')
    for index, c in enumerate(['site_id', 'waste_type', 'capacity_m3', 'sub_district', 'object_group']):
        mismatch[c] = sum((None if pd.isna(indexed.loc[b, c]) else indexed.loc[b, c]) != record[index] for b, record in attrs.items() if b in indexed.index)
    checks['registry_attribute_mismatches'] = sum(mismatch.values())
    train_bins = split['train']['bins'].copy()
    train_sites = split['train']['sites'].copy()
    for name, item in split.items():
        item['period'] = config['splits'][name]
        item['classes'] = {str(int(c)): int(n) for c, n in item['classes'].items()}
        item['unseen_bins'] = len(item['bins'] - train_bins)
        item['unseen_sites'] = len(item['sites'] - train_sites)
        for c in ['bins', 'sites', 'labeled_bins', 'labeled_sites']:
            item[c] = len(item[c])
        item['registry_coverage_pct'] = item['bins'] / len(registry) * 100
        item['missing_pct'] = {c: v / item['rows'] * 100 if item['rows'] else None for c, v in item['missing'].items()}
    daily_dictionary = [{'column': c, 'dtype': dtypes[c], 'cardinality': len(distinct[c]), 'missing': missing[c],
                         'missing_pct': missing[c] / rows * 100, 'examples': examples[c]} for c in HEADER]
    pd.DataFrame(daily_dictionary).to_csv(folder / 'daily_dictionary.csv', index=False)
    pd.DataFrame([{'class': int(c), 'count': n, 'share': n / sum(labels.values())} for c, n in sorted(labels.items())]).to_csv(folder / 'target_counts.csv', index=False)
    pd.DataFrame([{'bin_id': b, 'rows': n, 'labeled_rows': bin_labels[b]} for b, n in bins.items()]).to_csv(folder / 'labels_per_bin.csv', index=False)
    pd.DataFrame([{'site_id': s, 'labeled_rows': site_labels[s]} for s in distinct['site_id']]).to_csv(folder / 'labels_per_site.csv', index=False)
    registry.loc[~registry.id.isin(bins)].to_csv(folder / 'registry_only_bins.csv', index=False)
    pd.DataFrame([{'status': k, 'rows': v} for k, v in statuses.items()]).to_csv(folder / 'collection_status.csv', index=False)
    for name, counts in distributions.items():
        pd.DataFrame([{'value': value, 'target': target, 'rows': n} for (value, target), n in counts.items()]).to_csv(folder / f'target_by_{name}.csv', index=False)
    pd.DataFrame([{'split': s, 'feature': c, 'value': str(v), 'rows': n} for (s, c), counts in drift.items() for v, n in counts.items()]).to_csv(folder / 'feature_distribution_by_split.csv', index=False)
    report = {'passed': not any(checks.values()), 'checks': dict(checks), 'rows': rows, 'daily_bins': len(bins),
              'registry_bins': len(registry), 'registry_only_bins': len(set(registry.id) - set(bins)),
              'bins_no_labels': len(set(bins) - set(bin_labels)),
              'sites_no_labels': len(distinct['site_id'] - set(site_labels)),
              'date_min': str(min(distinct['date']).date()), 'date_max': str(max(distinct['date']).date()),
              'label_counts': {str(int(k)): v for k, v in labels.items()}, 'missing': dict(missing),
              'qr_zero': sum(n for (v, y), n in distributions['qr_range'].items() if v == 'zero'),
              'qr_max': float(max(distinct['qr_alerts'])), 'splits': split,
              'registry_attribute_mismatches': mismatch, 'versions': versions(), 'provenance': provenance(config)}
    write_json(folder / 'report.json', report)
    write_json(output_path(config, 'config_snapshot.json'), {k: v for k, v in config.items() if not k.startswith('_')})
    logging.info('Validation passed=%s; checks=%s', report['passed'], dict(checks))
    if not report['passed']:
        raise ValueError(f'Data audit failed; see {folder / "report.json"}')
    summarize_coverage(config)


def create_eda(config, args):
    summarize_coverage(config)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    plt.rcParams.update({'figure.dpi': 140, 'axes.spines.top': False, 'axes.spines.right': False,
                         'axes.titlesize': 12, 'font.size': 9})
    folder = output_path(config, 'validation')
    charts = output_path(config, 'charts', 'eda')
    charts.mkdir(parents=True, exist_ok=True)
    for field in ['waste_type', 'capacity_range', 'sub_district', 'object_group', 'qr_range']:
        table = pd.read_csv(folder / f'target_by_{field}.csv')
        labeled = table.loc[table.target >= 0]
        pivot = labeled.pivot_table(index='value', columns='target', values='rows', aggfunc='sum', fill_value=0)
        share = pivot.div(pivot.sum(axis=1), axis=0)
        ax = share.plot.barh(stacked=True, figsize=(9, max(3, len(share) * .23)), colormap='viridis')
        ax.set(xlabel='Share of synthetic labeled visits', ylabel=field, title=f'Synthetic worker class by {field}')
        ax.legend(title='Class', bbox_to_anchor=(1.02, 1))
        ax.figure.tight_layout()
        ax.figure.savefig(charts / f'target_by_{field}.png')
        plt.close(ax.figure)
    table = pd.read_csv(folder / 'target_by_date.csv')
    pivot = table.pivot_table(index='value', columns='target', values='rows', aggfunc='sum', fill_value=0).sort_index()
    pivot.index = pd.to_datetime(pivot.index)
    ax = pivot.loc[:, pivot.columns >= 0].plot(figsize=(10, 4), title='Synthetic labeled visits over time')
    ax.set(xlabel='Date', ylabel='Labeled visits')
    ax.legend(title='Class')
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6)); ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.figure.tight_layout(); ax.figure.savefig(charts / 'target_over_time.png'); plt.close(ax.figure)
    availability = pivot.loc[:, pivot.columns >= 0].sum(axis=1) / pivot.sum(axis=1)
    availability.rename('labeled_share').to_csv(folder / 'label_availability_over_time.csv')
    fig, ax = plt.subplots(figsize=(10, 3)); ax.plot(availability.index, availability.to_numpy()); ax.set(title='Synthetic label availability', ylabel='Labeled share', xlabel='Date'); ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6)); ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m')); fig.tight_layout(); fig.savefig(charts / 'label_availability.png'); plt.close(fig)
    counts = pd.read_csv(folder / 'target_counts.csv')
    fig, ax = plt.subplots(figsize=(6, 3)); ax.bar(counts['class'], counts['count'], color='#256d85'); ax.set(title='Synthetic worker target distribution', xlabel='Class', ylabel='Labeled visits'); fig.tight_layout(); fig.savefig(charts / 'target_distribution.png'); plt.close(fig)
    bins = pd.read_csv(folder / 'labels_per_bin.csv')
    fig, ax = plt.subplots(figsize=(7, 3)); ax.hist(bins.labeled_rows, bins=35, color='#256d85'); ax.set(title='Synthetic labels per history container', xlabel='Labeled days', ylabel='Containers'); fig.tight_layout(); fig.savefig(charts / 'labels_per_bin.png'); plt.close(fig)
    status = pd.read_csv(folder / 'collection_status.csv')
    ax = status.set_index('status').plot.barh(figsize=(7, 3), legend=False, title='Synthetic collection statuses'); ax.set(xlabel='Daily rows'); ax.figure.tight_layout(); ax.figure.savefig(charts / 'collection_status.png'); plt.close(ax.figure)
    qr = pd.read_csv(folder / 'target_by_qr_range.csv').groupby('value').rows.sum().reset_index()
    qr.to_csv(folder / 'qr_distribution.csv', index=False)
    ax = qr.set_index('value').plot.barh(figsize=(7, 3), legend=False, title='QR distribution including zero/missing'); ax.set(xlabel='Daily rows'); ax.figure.tight_layout(); ax.figure.savefig(charts / 'qr_distribution.png'); plt.close(ax.figure)
    interval_path = output_path(config, 'collection_interval_distribution.csv')
    if interval_path.exists():
        intervals = pd.read_csv(interval_path)
        intervals.to_csv(folder / 'collection_interval_distribution.csv', index=False)
        for feature, table in intervals.loc[intervals.days >= 0].groupby('feature'):
            pivot = table.pivot(index='days', columns='split', values='rows').fillna(0).sort_index()
            ax = pivot.plot(figsize=(9, 3), title=feature.replace('_', ' ')); ax.set(xlabel='Days since prior event', ylabel='Daily rows', yscale='log'); ax.figure.tight_layout(); ax.figure.savefig(charts / f'{feature}.png'); plt.close(ax.figure)
    from .common import read_json
    report = read_json(folder / 'report.json')
    classes = pd.DataFrame([{'split': name, 'class': int(float(c)), 'rows': n} for name, part in report['splits'].items() for c, n in part['classes'].items()])
    classes.to_csv(folder / 'class_distribution_by_split.csv', index=False)
    pivot = classes.pivot(index='split', columns='class', values='rows').fillna(0)
    ax = pivot.div(pivot.sum(axis=1), axis=0).plot.bar(stacked=True, figsize=(7, 4), colormap='viridis', title='Synthetic class proportions by temporal split'); ax.figure.tight_layout(); ax.figure.savefig(charts / 'class_distribution_by_split.png'); plt.close(ax.figure)
    if output_path(config, 'features_manifest.json').exists():
        from .features import NUMERIC
        moments = {}
        for split in ['train','validation','test']:
            values = config['_frames'][split][NUMERIC].to_numpy(dtype=float)
            moments[split] = {'rows':len(values),'count':np.isfinite(values).sum(axis=0),
                'sum':np.nansum(values,axis=0),'squares':np.nansum(values**2,axis=0)}
        rows = []
        for split, item in moments.items():
            mean = np.divide(item['sum'], item['count'], out=np.full(len(NUMERIC), np.nan), where=item['count'] > 0)
            variance = np.divide(item['squares'], item['count'], out=np.full(len(NUMERIC), np.nan), where=item['count'] > 0) - mean**2
            for i, feature in enumerate(NUMERIC):
                rows.append({'split': split, 'feature': feature, 'labeled_rows': item['rows'], 'known_rows': int(item['count'][i]),
                             'missing_pct': 100 * (1 - item['count'][i] / item['rows']), 'mean': mean[i], 'std_population': np.sqrt(max(0, variance[i]))})
        drift = pd.DataFrame(rows)
        drift.to_csv(folder / 'numeric_feature_drift.csv', index=False)
        shown = ['qr_alerts', 'collections_last_28d', 'days_since_last_successful_collection', 'collections_last_90d', 'days_since_previous_worker_rating', 'previous_worker_rating']
        fig, axes = plt.subplots(2, 3, figsize=(11, 6))
        for feature, ax in zip(shown, axes.flat):
            part = drift.loc[drift.feature == feature].set_index('split').reindex(['train','validation','test'])
            ax.bar(part.index, part['mean'], color='#256d85'); ax.set(title=feature.replace('_', ' '), ylabel='Mean on labeled rows'); ax.tick_params(axis='x', rotation=40)
        fig.suptitle('Active feature drift: sampled training vs full labeled evaluation'); fig.tight_layout(); fig.savefig(charts / 'numeric_feature_drift.png'); plt.close(fig)
    logging.info('EDA tables=%s; charts=%s', folder, charts)
