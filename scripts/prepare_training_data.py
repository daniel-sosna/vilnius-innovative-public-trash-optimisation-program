"""Run the existing population/calendar algorithms on the supplied local exports.

From the repository root:
    python scripts/prepare_training_data.py --years 3 --end 2026-10-09
For an explicit interval use --start YYYY-MM-DD --end YYYY-MM-DD instead.
Produces feature data, not a labelled fill-level training set. No database writes.
"""

import argparse
import csv
import hashlib
import json
import math
import platform
import sys
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / 'backend'
DATA = BACKEND / 'data'
sys.path.insert(0, str(BACKEND))

from app.interfaces.bin_population.allocation import (
    DEFAULT_SUPPRESSED_DENSITY, BinRecord, allocate, parse_polygons,
)
from app.interfaces.bin_days.simulation import (
    WARMUP_DAYS, Parameters, holiday_ordinals, simulate_bin,
)

PARAMS = Parameters(42, 0.028, 0.40, 0.70, 2)
INPUTS = {
    'sites': 'sites_202610092000.csv',
    'bins': 'bins_202610091935.csv',
    'bin_schedule': 'bin_schedule_202610100342.csv',
    'bin_hist': 'bin_hist_202610091935.csv',
    'population': 'population_density_1ha.geojson',
}
COLUMNS = [
    'bin_id', 'date', 'day_of_week', 'week_of_year', 'month', 'season',
    'site_id', 'waste_type', 'capacity_m3', 'sub_district', 'object_group',
    'population_cell_id', 'resident_factor', 'collection_status',
    'holidays_since_last_collection', 'collections_last_28d', 'missed_collections_28d',
]


def rows(name):
    with (DATA / INPUTS[name]).open(encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle))


def nullable(value):
    return None if value == 'NULL' else value


def unique_by_id(records):
    result = {int(row['id']): row for row in records}
    if len(result) != len(records):
        raise ValueError('Duplicate source ids')
    return result


def digest(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def iso_date(value):
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError('Expected a YYYY-MM-DD date') from None


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    interval = parser.add_mutually_exclusive_group()
    interval.add_argument('--years', type=int, choices=range(1, 6),
                          help='Calendar years backwards from the end date (default: 3)')
    interval.add_argument('--start', type=iso_date, help='Explicit inclusive first date')
    parser.add_argument('--end', type=iso_date,
                        help='Inclusive last date (default: latest source history date)')
    args = parser.parse_args()
    if args.start is None and args.years is None:
        args.years = 3
    return args


def date_range(args, history):
    if not history:
        raise ValueError('Source history is empty; cannot determine its date range')
    end = args.end or max(date.fromisoformat(row['date'][:10]) for row in history)
    if args.start is not None:
        start = args.start
    else:
        try:
            anniversary = end.replace(year=end.year - args.years)
        except ValueError:
            # A leap-day end date maps to Feb 28 in a non-leap year.
            anniversary = end.replace(year=end.year - args.years, day=28)
        start = anniversary + timedelta(days=1)
    days = (end - start).days + 1
    if not 1 <= days <= 1827:
        raise ValueError('The interval must contain 1 to 1827 days (at most five years)')
    return start, end


def main():
    args = parse_args()
    for filename in INPUTS.values():
        if not (DATA / filename).is_file():
            raise FileNotFoundError(filename)
    sites = unique_by_id(rows('sites'))
    bins = unique_by_id(rows('bins'))
    schedules = rows('bin_schedule')
    history = rows('bin_hist')
    start, end = date_range(args, history)
    days = (end - start).days + 1
    print(f'Interval: {start}..{end} inclusive ({days} days)', flush=True)
    unique_by_id(schedules)
    unique_by_id(history)
    if any(int(row['site_id']) not in sites for row in bins.values()):
        raise ValueError('Bin references missing site')
    if any(int(row['bin_id']) not in bins for row in schedules + history):
        raise ValueError('Schedule/history references missing bin')
    planned = defaultdict(set)
    for row in schedules:
        planned[int(row['bin_id'])].add(date.fromisoformat(row['date']))

    records = [BinRecord(
        key, row['waste_type'],
        None if nullable(row['capacity_m3']) is None else float(row['capacity_m3']),
        float(row['latitude']), float(row['longitude']), nullable(row['object_group']),
    ) for key, row in sorted(bins.items())]
    polygons = parse_polygons(DATA / INPUTS['population'], DEFAULT_SUPPRESSED_DENSITY)
    print(f'Allocating {len(polygons)} population polygons to {len(records)} bins...', flush=True)
    allocation = allocate(records, polygons)
    if set(allocation.factor_by_bin) != set(bins):
        raise ValueError('Incomplete population allocation')
    if any(not math.isfinite(v) or v < 0 for v in allocation.factor_by_bin.values()):
        raise ValueError('Invalid resident factor')
    for stats in allocation.stats.values():
        if not math.isclose(stats.allocated + stats.unallocated,
                            sum(p.residents for p in polygons), rel_tol=1e-9):
            raise ValueError('Population conservation failed')

    population_file = DATA / 'bin_population.csv'
    with population_file.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['bin_id', 'population_cell_id', 'resident_factor'])
        for key in sorted(bins):
            writer.writerow([key, allocation.cell_by_bin[key], allocation.factor_by_bin[key]])

    eligible = [key for key in sorted(bins)
                if nullable(bins[key]['sub_district']) is not None and planned.get(key)]
    holiday_days = holiday_ordinals(start - timedelta(days=WARMUP_DAYS), end)
    statuses = Counter()
    feature_file = DATA / f'bin_days_{start:%Y%m%d}_{end:%Y%m%d}.csv'
    partial_file = feature_file.with_suffix('.csv.partial')
    total = 0
    print(f'Building {days} days for {len(eligible)} eligible bins...', flush=True)
    with partial_file.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(COLUMNS)
        for index, key in enumerate(eligible, 1):
            row = bins[key]
            for day, status, *features in simulate_bin(key, planned[key], start, end, PARAMS, holiday_days):
                writer.writerow([
                    key, day.isoformat(), day.isoweekday(), day.isocalendar().week,
                    day.month, day.month % 12 // 3 + 1, int(row['site_id']), row['waste_type'],
                    nullable(row['capacity_m3']), row['sub_district'], nullable(row['object_group']),
                    allocation.cell_by_bin[key], allocation.factor_by_bin[key], status, *features,
                ])
                statuses[status] += 1
                total += 1
            if index % 1000 == 0:
                print(f'Processed {index}/{len(eligible)} bins; {total} rows', flush=True)
    expected = len(eligible) * days
    if total != expected:
        raise ValueError(f'Expected {expected} feature rows, got {total}')
    partial_file.replace(feature_file)

    # Companion observations for the future fill generator; never mixed into
    # synthetic collection_status. Latest timestamp wins, then highest id.
    latest = {}
    for row in history:
        key = (int(row['bin_id']), row['date'][:10])
        previous = latest.get(key)
        if previous is None or (row['date'], int(row['id'])) > (previous['date'], int(previous['id'])):
            latest[key] = row
    daily_file = DATA / 'bin_hist_daily.csv'
    with daily_file.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['bin_id', 'date', 'history_id', 'observed_at', 'was_serviced',
                         'non_serviced_reason', 'fill_level'])
        for (key, day), row in sorted(latest.items()):
            writer.writerow([key, day, row['id'], row['date'], row['was_serviced'],
                             nullable(row['non_serviced_reason']), nullable(row['fill_level'])])

    source_code = [Path(__file__),
                   BACKEND / 'app/interfaces/bin_population/allocation.py',
                   BACKEND / 'app/interfaces/bin_days/simulation.py']
    manifest = {
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'branch': 'ml-training',
        'kind': 'bin-day features plus separate observed daily history',
        'ready_for_fill_level_training': False,
        'limitation': 'All source fill_level values are NULL. The synthetic fill-level target generator is not implemented in this branch.',
        'range': {'start': start.isoformat(), 'end': end.isoformat(), 'days': days,
                  'years': args.years,
                  'rationale': 'Requested retrospective interval ending at the anchor date; '
                               'its previous anniversary is excluded and its end date included'},
        'observed_history_range': {
            'start': min(row['date'][:10] for row in history),
            'end': max(row['date'][:10] for row in history),
        },
        'simulation': asdict(PARAMS),
        'warmup_days': WARMUP_DAYS,
        'suppressed_density_per_ha': DEFAULT_SUPPRESSED_DENSITY,
        'runtime': {'python': platform.python_version(), 'holidays': version('holidays')},
        'reproduce_from_repo_root': (
            f'python scripts/prepare_training_data.py --years {args.years} --end {end}'
            if args.years is not None else
            f'python scripts/prepare_training_data.py --start {start} --end {end}'
        ),
        'inputs': {name: {'file': file, 'sha256': digest(DATA / file)} for name, file in INPUTS.items()},
        'source_code_sha256': {p.relative_to(ROOT).as_posix(): digest(p) for p in source_code},
        'counts': {'sites': len(sites), 'bins': len(bins), 'schedule': len(schedules),
                   'history': len(history), 'population_polygons': len(polygons),
                   'eligible_bins': len(eligible), 'bin_days': total,
                   'excluded_without_sub_district': sum(nullable(r['sub_district']) is None for r in bins.values()),
                   'excluded_without_schedule': sum(nullable(r['sub_district']) is not None and not planned.get(k) for k, r in bins.items()),
                   'history_daily': len(latest),
                   'observed_non_null_fill_levels': sum(nullable(r['fill_level']) is not None for r in history)},
        'status_counts': dict(statuses),
        'population': {key: {'residential_bins': s.residential_bins, 'points': s.points,
                             'allocated_residents': s.allocated, 'unallocated_residents': s.unallocated}
                       for key, s in allocation.stats.items()},
        'outputs': {p.name: {'bytes': p.stat().st_size, 'sha256': digest(p)}
                    for p in [population_file, feature_file, daily_file]},
        'assumptions': [
            'Registry attributes are snapshots applied to all dates.',
            'Every eligible bin is assumed to exist on every generated day; installation/removal dates are unavailable.',
            'October schedule repeats over the requested range using existing cycle detection.',
            'Resident allocation is estimated; suppressed density <11 is treated as 5 per ha.',
            'Collection outcomes and look-back features are synthetic with the recorded seed.',
            'bin_hist_daily contains observed events and is separate from synthetic features.',
            'For multiple same-day history events the latest timestamp wins, then highest id.',
            'No target values are invented and no database is modified.',
        ],
    }
    manifest_text = json.dumps(manifest, ensure_ascii=False, indent=2) + '\n'
    (DATA / f'training_data_manifest_{start:%Y%m%d}_{end:%Y%m%d}.json').write_text(
        manifest_text, encoding='utf-8')
    (DATA / 'training_data_manifest.json').write_text(manifest_text, encoding='utf-8')
    print(json.dumps(manifest['counts'], ensure_ascii=False), flush=True)
    print(f'Feature CSV: {feature_file}', flush=True)


if __name__ == '__main__':
    main()
