"""CSV source adapter; output is returned in memory unless the caller exports it."""
import argparse
from pathlib import Path
import pandas as pd

from .features import SAFE_COUNTERS, build_next_day_features, check_sequence
from .runtime import FillPredictor


def history_batches(path, chunk_rows=100000):
    carry = None
    previous_bin = None
    columns = ['bin_id', 'date', 'collection_status', 'fill_level'] + SAFE_COUNTERS
    with pd.read_csv(path, usecols=columns, chunksize=chunk_rows, keep_default_na=False, na_values=['', 'NULL']) as reader:
        for chunk in reader:
            chunk['date'] = pd.to_datetime(chunk.date, errors='raise')
            if carry is not None:
                chunk = pd.concat([carry, chunk], ignore_index=True)
            last = chunk.bin_id.iloc[-1]
            carry = chunk.loc[chunk.bin_id == last].copy()
            complete = chunk.loc[chunk.bin_id != last].copy()
            if len(complete):
                for key, part in complete.groupby('bin_id', sort=False):
                    if previous_bin is not None and key <= previous_bin:
                        raise ValueError('CSV must be sorted by bin_id then date')
                    check_sequence(part)
                    previous_bin = key
                yield complete
        if carry is not None:
            check_sequence(carry)
            if previous_bin is not None and carry.bin_id.iloc[0] <= previous_bin:
                raise ValueError('Repeated final bin block')
            yield carry


def predict_csv(product, daily_csv, registry_df, today, population_df=None, chunk_rows=100000):
    predictor = FillPredictor.load(product)
    day = pd.Timestamp(today).normalize() + pd.Timedelta(days=1)
    registry = registry_df.rename(columns={'id': 'bin_id'}).copy()
    mapping = predictor.district_aliases
    canonical = registry.sub_district.astype('string').str.strip().str.replace(r'\s+', ' ', regex=True).map(
        {**{v: v for v in mapping.values()}, **mapping})
    counts = canonical.groupby(registry.site_id).nunique()
    registry.loc[registry.site_id.isin(counts.index[counts > 1]), 'sub_district'] = '__AMBIGUOUS__'
    parts, seen = [], set()
    for batch in history_batches(daily_csv, chunk_rows):
        ids = batch.bin_id.unique()
        roster = registry.loc[registry.bin_id.isin(ids)]
        if len(roster) != len(ids):
            raise ValueError('History contains bins outside registry')
        safe = batch.loc[batch.date == day, ['bin_id', 'date'] + SAFE_COUNTERS]
        history = batch.loc[batch.date < day]
        parts.append(predictor.predict_next_day(history, roster, today, safe, population_df))
        seen.update(ids)
    missing = registry.loc[~registry.bin_id.isin(seen)]
    if len(missing):
        empty = pd.DataFrame(columns=['bin_id', 'date', 'collection_status', 'fill_level'])
        parts.append(predictor.predict_next_day(empty, missing, today, population_df=population_df))
    result = pd.concat(parts, ignore_index=True)
    if result.bin_id.duplicated().any() or set(result.bin_id) != set(registry.bin_id):
        raise ValueError('CSV prediction coverage failed')
    return result.set_index('bin_id').loc[registry.bin_id].reset_index()


def main():
    parser = argparse.ArgumentParser(description='Forecast tomorrow from immutable CSV history; no implicit export')
    parser.add_argument('--product', required=True)
    parser.add_argument('--daily', required=True)
    parser.add_argument('--registry', required=True)
    parser.add_argument('--population')
    parser.add_argument('--today', required=True)
    parser.add_argument('--output', help='Explicitly export the two-column result, if requested')
    args = parser.parse_args()
    registry = pd.read_csv(args.registry, keep_default_na=False, na_values=['', 'NULL'])
    population = pd.read_csv(args.population, keep_default_na=False, na_values=['', 'NULL']) if args.population else None
    result = predict_csv(args.product, args.daily, registry, args.today, population)
    if args.output:
        result.to_csv(args.output, index=False)
    print(result.head().to_string(index=False))
    print(f'{len(result)} predictions for {(pd.Timestamp(args.today) + pd.Timedelta(days=1)).date()}')


if __name__ == '__main__':
    main()
