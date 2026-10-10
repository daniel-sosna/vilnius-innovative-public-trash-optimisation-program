"""Pure in-memory active feature contract shared by fitting and inference."""
import numpy as np
import pandas as pd

SUCCESS = {'collected', 'retry_collected'}
STATUSES = SUCCESS | {'none', 'failed', 'missed'}
NUMERIC = ['day_of_week', 'week_of_year', 'month', 'capacity_m3', 'resident_factor',
           'holidays_since_last_collection', 'collections_last_28d', 'missed_collections_28d',
           'qr_alerts', 'days_since_last_successful_collection', 'days_since_last_collection_attempt',
           'days_since_previous_worker_rating', 'previous_worker_rating', 'collections_last_7d',
           'collections_last_90d', 'missed_collections_last_90d']
CATEGORICAL = ['season', 'waste_type', 'sub_district', 'object_group', 'previous_collection_status']
FEATURES = NUMERIC + CATEGORICAL
SAFE_COUNTERS = ['holidays_since_last_collection', 'collections_last_28d', 'missed_collections_28d', 'qr_alerts']
HISTORY = [c for c in NUMERIC if c not in ['day_of_week', 'week_of_year', 'month', 'capacity_m3', 'resident_factor']]


def capacity_range(values):
    return pd.cut(values, [-np.inf, 0, .24, 1.1, 3, 5, np.inf],
                  labels=['invalid', 'small', 'medium', 'large', 'very_large', 'extra_large']).astype('string').fillna('missing')


def check_sequence(frame):
    if frame.bin_id.nunique() != 1 or frame.date.duplicated().any():
        raise ValueError('Expected one bin with unique dates per block')
    if len(frame) > 1 and not frame.date.diff().iloc[1:].eq(pd.Timedelta(days=1)).all():
        raise ValueError(f'Nonconsecutive or unordered dates for bin {frame.bin_id.iloc[0]}')


def quality_flags(frame):
    conditions = {
        'missing_qr_history': frame.qr_alerts.isna().to_numpy(),
        'missing_object_group': frame.object_group.isna().to_numpy() | frame.object_group.eq('__MISSING__').fillna(False).to_numpy(dtype=bool),
        'ambiguous_district': frame.sub_district.eq('__AMBIGUOUS__').fillna(False).to_numpy(dtype=bool) | frame.sub_district.isna().to_numpy(),
        'invalid_capacity': frame.capacity_m3.isna().to_numpy() | (frame.capacity_m3 <= 0).to_numpy(),
        'no_daily_history': ~frame.has_daily_history.to_numpy(dtype=bool),
        'no_historical_labels': (frame.history_label_count == 0).to_numpy(),
    }
    result = np.full(len(frame), '', dtype=object)
    count = np.zeros(len(frame), dtype=np.int8)
    for name, mask in conditions.items():
        result[mask] = np.where(count[mask] == 0, name, result[mask] + '|' + name)
        count[mask] += 1
    result[count == 0] = 'complete'
    result[count > 1] = 'multiple_issues:' + result[count > 1]
    return result


def normalize(frame, district_aliases, ambiguous_site_ids=()):
    frame = frame.copy()
    raw = frame.sub_district.astype('string').str.strip().str.replace(r'\s+', ' ', regex=True)
    # Accept already canonical names as well as reviewed raw aliases.
    mapping = {**{v: v for v in district_aliases.values()}, **district_aliases}
    frame['sub_district'] = raw.map(mapping).fillna('__AMBIGUOUS__')
    frame.loc[frame.site_id.isin(ambiguous_site_ids), 'sub_district'] = '__AMBIGUOUS__'
    frame['object_group'] = frame.object_group.astype('string').str.strip().replace('', pd.NA).fillna('__MISSING__')
    frame['capacity_m3'] = pd.to_numeric(frame.capacity_m3, errors='raise')
    frame['capacity_range'] = capacity_range(frame.capacity_m3)
    frame.loc[~np.isfinite(frame.capacity_m3) | (frame.capacity_m3 <= 0), 'capacity_m3'] = np.nan
    frame['input_quality_flag'] = quality_flags(frame)
    frame['season'] = pd.to_numeric(frame.season, errors='raise').astype('Int64').astype('string')
    for column in CATEGORICAL:
        frame[column] = frame[column].astype('string').fillna('__MISSING__')
    for column in NUMERIC:
        frame[column] = pd.to_numeric(frame[column], errors='raise').replace([np.inf, -np.inf], np.nan).astype('float32')
    return frame


def engineer_bins(frame, district_aliases, *, verify_source=True, ambiguous_site_ids=()):
    frame = frame.copy().reset_index(drop=True)
    keys = frame.bin_id
    def prior(values):
        return values.groupby(keys, sort=False).shift(1)
    def rolling(values, window):
        return prior(values.astype(float)).groupby(keys, sort=False).rolling(window, min_periods=window).sum().reset_index(level=0, drop=True).sort_index()
    date = frame.date
    success = frame.collection_status.isin(SUCCESS)
    attempt = ~frame.collection_status.eq('none')
    known = frame.fill_level.notna()
    frame['has_daily_history'] = True
    for name, event in [('last_successful_collection', success), ('last_collection_attempt', attempt), ('previous_worker_rating', known)]:
        previous = prior(date.where(event).groupby(keys, sort=False).ffill())
        frame['days_since_' + name] = (date - previous).dt.days.astype(float)
    frame['previous_collection_status'] = prior(frame.collection_status)
    frame['previous_worker_rating'] = prior(frame.fill_level.groupby(keys, sort=False).ffill())
    for window in [7, 90]:
        frame[f'collections_last_{window}d'] = rolling(success, window)
    frame['missed_collections_last_90d'] = rolling(frame.collection_status.eq('missed'), 90)
    frame['history_label_count'] = known.astype(int).groupby(keys, sort=False).cumsum() - known.astype(int)
    if verify_source:
        for name, event in [('collections_last_28d', success), ('missed_collections_28d', frame.collection_status.eq('missed'))]:
            computed = rolling(event, 28)
            mask = computed.notna()
            if not np.array_equal(computed[mask].to_numpy(), frame.loc[mask, name].to_numpy()):
                raise ValueError(f'{name} does not match strictly prior history')
        reset = prior(success).astype('boolean').fillna(False) & frame.qr_alerts.notna()
        if not frame.loc[reset, 'qr_alerts'].eq(0).all():
            raise ValueError('QR counter does not reset the day after success')
    return normalize(frame, district_aliases, ambiguous_site_ids)


def engineer_bin(frame, district_aliases, **kwargs):
    check_sequence(frame)
    return engineer_bins(frame, district_aliases, **kwargs)


def registry_rows(registry_df, day, population_df=None):
    registry = registry_df.rename(columns={'id': 'bin_id'}).copy()
    required = ['bin_id', 'site_id', 'waste_type', 'capacity_m3', 'sub_district', 'object_group']
    if not set(required).issubset(registry) or registry.bin_id.isna().any() or registry.bin_id.duplicated().any():
        raise ValueError('Registry requires valid unique bin IDs and static columns')
    frame = registry[required + [c for c in ['resident_factor', 'population_cell_id'] if c in registry]].copy()
    if population_df is not None:
        if population_df.bin_id.duplicated().any():
            raise ValueError('Population snapshot contains duplicate bin IDs')
        frame = frame.drop(columns=['resident_factor', 'population_cell_id'], errors='ignore').merge(
            population_df[['bin_id', 'population_cell_id', 'resident_factor']], on='bin_id', how='left', validate='one_to_one')
    for c in ['resident_factor', 'population_cell_id']:
        if c not in frame:
            frame[c] = np.nan
    frame['date'] = pd.Timestamp(day)
    frame['day_of_week'] = pd.Timestamp(day).isoweekday()
    frame['week_of_year'] = pd.Timestamp(day).isocalendar().week
    frame['month'] = pd.Timestamp(day).month
    frame['season'] = (pd.Timestamp(day).month % 12) // 3 + 1
    for c in HISTORY:
        frame[c] = np.nan
    frame['previous_collection_status'] = pd.NA
    frame['fill_level'] = np.nan
    frame['collection_status'] = 'none'
    frame['has_daily_history'] = False
    frame['history_label_count'] = 0
    return frame


def build_next_day_features(history_df, registry_df, today, day_counters_df=None,
                            population_df=None, district_aliases=None):
    """Return feature rows for T+1; never write or modify caller frames."""
    day = pd.Timestamp(today).normalize() + pd.Timedelta(days=1)
    if pd.isna(day):
        raise ValueError('Invalid today date')
    mapping = district_aliases or {}
    rows = registry_rows(registry_df, day, population_df)
    canonical = rows.sub_district.astype('string').str.strip().str.replace(r'\s+', ' ', regex=True).map(
        {**{v: v for v in mapping.values()}, **mapping})
    district_counts = canonical.groupby(rows.site_id).nunique()
    ambiguous_sites = district_counts.index[district_counts > 1]
    rows.loc[rows.site_id.isin(ambiguous_sites), 'sub_district'] = '__AMBIGUOUS__'
    raw = history_df.copy()
    required = ['bin_id', 'date', 'collection_status', 'fill_level']
    if not set(required).issubset(raw):
        raise ValueError('History requires bin_id, date, collection_status and fill_level')
    raw['date'] = pd.to_datetime(raw.date, errors='raise')
    if raw.date.isna().any() or raw.bin_id.isna().any():
        raise ValueError('History contains missing dates or IDs')
    past = raw.loc[raw.date < day, required].copy()
    if past.duplicated(['bin_id', 'date']).any():
        raise ValueError('Duplicate history bin/date key')
    if not past.bin_id.isin(rows.bin_id).all():
        raise ValueError('History contains bins outside the supplied registry')
    if not past.collection_status.isin(STATUSES).all():
        raise ValueError('Invalid historical collection status')
    past['fill_level'] = pd.to_numeric(past.fill_level, errors='raise')
    if not past.fill_level.dropna().isin(range(5)).all():
        raise ValueError('Historical assessment must be NULL or integer 0..4')
    past = past.sort_values(['bin_id', 'date']).reset_index(drop=True)
    differences = past.groupby('bin_id', sort=False).date.diff().dropna()
    if not differences.eq(pd.Timedelta(days=1)).all():
        raise ValueError('Nonconsecutive historical dates')
    if day_counters_df is not None:
        counters = day_counters_df.copy()
        if not {'bin_id', 'date'}.issubset(counters):
            raise ValueError('Safe counters require bin_id and date')
        counters['date'] = pd.to_datetime(counters.date, errors='raise')
        counters = counters.loc[counters.date == day]
        if counters.bin_id.duplicated().any() or not counters.bin_id.isin(rows.bin_id).all():
            raise ValueError('Invalid safe-counter IDs or duplicate forecast-day keys')
        rows = rows.set_index('bin_id')
        for c in SAFE_COUNTERS:
            if c in counters:
                values = pd.to_numeric(counters[c], errors='raise')
                if not np.isfinite(values.dropna()).all() or (values.dropna() < 0).any():
                    raise ValueError(f'Invalid safe counter: {c}')
                rows.loc[counters.bin_id, c] = values.to_numpy()
        rows = rows.reset_index()
    # Reconstruct only counters whose complete observation windows are known.
    success = past.collection_status.isin(SUCCESS)
    recent = past.date >= day - pd.Timedelta(days=28)
    window_size = past.loc[recent].groupby('bin_id').size()
    complete_ids = window_size.index[window_size == 28]
    for c, event in [('collections_last_28d', success), ('missed_collections_28d', past.collection_status.eq('missed'))]:
        counts = event.loc[recent].groupby(past.loc[recent, 'bin_id']).sum()
        values = rows.bin_id.map(counts).where(rows.bin_id.isin(complete_ids))
        rows[c] = rows[c].fillna(values)
    last = past.groupby('bin_id', sort=False).tail(1).set_index('bin_id')
    reset_ids = last.index[(last.date == day - pd.Timedelta(days=1)) & last.collection_status.isin(SUCCESS)]
    rows.loc[rows.bin_id.isin(reset_ids) & rows.qr_alerts.isna(), 'qr_alerts'] = 0.
    if rows.holidays_since_last_collection.isna().any() and len(past):
        import holidays
        calendar = holidays.country_holidays('LT', years=range(past.date.min().year, day.year + 1))
        dates = sorted(pd.Timestamp(d) for d in calendar if pd.Timestamp(d) < day)
        last_success = past.loc[success].groupby('bin_id').date.max()
        for index in rows.index[rows.holidays_since_last_collection.isna()]:
            key = rows.at[index, 'bin_id']
            if key in last_success and key in last.index and last.at[key, 'date'] == day - pd.Timedelta(days=1):
                rows.at[index, 'holidays_since_last_collection'] = sum(d > last_success[key] for d in dates)
    # Full continuous histories permit vectorized lag/window calculation.
    combined = pd.concat([past, rows], ignore_index=True).sort_values(['bin_id', 'date']).reset_index(drop=True)
    out = engineer_bins(combined, mapping, verify_source=False)
    out = out.loc[out.date == day].copy()
    out['has_daily_history'] = out.bin_id.isin(past.bin_id)
    # A stale history cannot pretend that its last row occurred yesterday.
    fresh_ids = last.index[last.date == day - pd.Timedelta(days=1)]
    stale = out.has_daily_history & ~out.bin_id.isin(fresh_ids)
    out.loc[stale, ['previous_collection_status']] = '__MISSING__'
    out.loc[stale, ['collections_last_7d', 'collections_last_90d', 'missed_collections_last_90d']] = np.nan
    out['input_quality_flag'] = quality_flags(out)
    return out.set_index('bin_id').loc[rows.bin_id].reset_index()


def feature_dictionary():
    records = []
    for c in FEATURES:
        if c in SAFE_COUNTERS:
            source, window = c, 'Source D row; counter excludes outcomes on D'
        elif c in ['previous_worker_rating', 'days_since_previous_worker_rating']:
            source, window = 'fill_level/date', 'Latest known assessment date < D'
        elif c.startswith('days_since_') or c == 'previous_collection_status':
            source, window = 'collection_status/date', 'Prior qualifying event, or D-1 status'
        elif c in ['collections_last_7d', 'collections_last_90d', 'missed_collections_last_90d']:
            source, window = 'collection_status', '[D-7,D-1]' if '7d' in c else '[D-90,D-1]'
        elif c in ['day_of_week', 'week_of_year', 'month', 'season']:
            source, window = 'date', 'Forecast date D'
        else:
            source, window = c, 'Static registry/population snapshot'
        records.append({'feature': c, 'source': source, 'window': window,
                        'missing_meaning': 'Unknown input/history; genuine zero is retained',
                        'used_by_model': True})
    return records
