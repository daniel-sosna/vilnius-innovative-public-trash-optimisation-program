import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
from time import perf_counter

from app.core.config import data_dir
from app.services.adequacy_artifacts import output_directory, month_bounds
from app.services.container_adequacy import (
    Policy, aggregate_daily, build_snapshot, file_hash, latest_export,
    load_registry, make_document, publish,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate portable completed-month residential adequacy GeoJSON (synthetic fill).")
    period = parser.add_mutually_exclusive_group(required=True)
    period.add_argument('--month', help='Completed calendar month YYYY-MM')
    period.add_argument('--all-complete', action='store_true')
    parser.add_argument('--daily', type=Path, required=True, help='Explicit immutable enriched bin-day CSV; never the base CSV')
    parser.add_argument('--data-dir', type=Path, default=data_dir())
    parser.add_argument('--bins', type=Path, help='Registry override')
    parser.add_argument('--population', type=Path, help='Population GeoJSON override')
    parser.add_argument('--regenerate', action='store_true', help='Explicitly replace results whose inputs or policy changed')
    for name, default in asdict(Policy()).items():
        parser.add_argument('--' + name.replace('_', '-'), type=type(default), default=default)
    args = parser.parse_args()
    started = perf_counter()
    try:
        policy = Policy(**{key: getattr(args, key) for key in asdict(Policy())})
        if args.month:
            month_bounds(args.month)
        sources = {name: latest_export(args.data_dir, name) for name in ('sites', 'bins', 'bin_hist')}
        sources['bins'] = args.bins or sources['bins']
        sources['population'] = args.population or args.data_dir / 'population_density_1ha.geojson'
        sources['daily_synthetic_fill'] = args.daily
        for name, path in sources.items():
            if not path.is_file():
                raise ValueError(f'Missing {name}: {path}. Add the required export; do not run bin_sync.')
        hashes = {name: file_hash(path) for name, path in sources.items()}
        bins, registry = load_registry(sources['bins'])
        snapshot = build_snapshot(bins, sources['population'], policy)
        daily = aggregate_daily(args.daily, registry, snapshot['bin_to_point'])
        months = [args.month] if args.month else daily['complete_months']
        if not months:
            raise ValueError('No completed months in the supplied daily cohort calendar')
        print(json.dumps({'complete_months': daily['complete_months'], 'coverage': daily['coverage'],
                          'rows': daily['rows'], 'excluded_registry_bins': len(daily['excluded_bins']),
                          'pressure_thresholds': snapshot['thresholds'], 'read_seconds': round(perf_counter() - started, 2)}))
        failed = False
        for month in months:
            tick = perf_counter()
            try:
                document = make_document(snapshot, daily, month, hashes, policy)
                path, status = publish(document, output_directory(args.data_dir), args.regenerate)
                print(json.dumps({'month': month, 'status': status, 'path': str(path.resolve()),
                                  'revision': file_hash(path), 'quality': document['analysis']['quality']['point_summaries'],
                                  'category_counts': document['analysis']['quality']['category_counts'],
                                  'seconds': round(perf_counter() - tick, 2)}))
            except (ValueError, OSError, ImportError) as error:
                failed = True
                print(f'{month}: {error}', file=sys.stderr)
        if any(file_hash(path) != hashes[name] for name, path in sources.items()):
            raise ValueError('Source changed during analysis; keep inputs immutable and regenerate explicitly')
        return int(failed)
    except (ValueError, OSError, ImportError) as error:
        print(f'Analysis failed: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
