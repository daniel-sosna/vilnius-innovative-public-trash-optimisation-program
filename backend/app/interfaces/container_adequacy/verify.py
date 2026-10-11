"""Repeatable numerical/artifact audit, not a test-suite dependency.

Run: python -m app.interfaces.container_adequacy.verify --data-dir data
"""
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import csv
from dataclasses import replace
import json
from math import isclose
from pathlib import Path
import tempfile

from app.services.container_adequacy import (
    Assessments, Policy, WASTE_TYPES, aggregate_daily, build_snapshot, classify,
    file_hash, fit_assessments, latest_export, load_registry, publish,
)
from app.services.adequacy_artifacts import get_analysis, list_analyses, output_directory, validate_artifact
from app.interfaces.bin_population.allocation import BinRecord


def check(condition, message):
    if not condition:
        raise ValueError(message)


def expect_failure(action):
    try:
        action()
    except (ValueError, OSError):
        return
    raise ValueError('Invalid operation unexpectedly succeeded')


def audit(directory: Path, sensitivity: bool) -> dict:
    bins, registry = load_registry(latest_export(directory, 'bins'))
    policy = Policy()
    snapshot = build_snapshot(bins, directory / 'population_density_1ha.geojson', policy)
    with tempfile.TemporaryDirectory(dir=directory) as temporary:
        fixture = Path(temporary) / 'population.geojson'
        ring = [[25.0,54.7],[25.001,54.7],[25.001,54.701],[25.0,54.701],[25.0,54.7]]
        def examples(densities):
            fixture.write_text(json.dumps({'type': 'FeatureCollection', 'features': [
                {'type': 'Feature', 'properties': {'OBJECTID': i, 'Shape_Area': 10000, 'gyv_sk_1ha': str(d)},
                 'geometry': {'type': 'Polygon', 'coordinates': [ring]}} for i, d in enumerate(densities, 1)]}), encoding='utf-8')
            return build_snapshot([BinRecord(1, WASTE_TYPES[0], 3, 54.7005,25.0005,'Daugiabučiai namai')], fixture, policy)
        single = examples([600])['areas'][0]['properties']
        check(single['pressure'] == 200 and single['attributed_capacity_m3'] == 3, '600-resident pressure')
        shared = [f['properties'] for f in examples([100,200])['areas'] if f['properties']['waste_type'] == WASTE_TYPES[0]]
        check([p['attributed_capacity_m3'] for p in shared] == [1,2], 'Shared capacity example')
        check(all(p['pressure'] == 100 for p in shared), 'Shared pressure')
        unknown = examples([0])['areas'][0]['properties']
        check(unknown['reasons'] == ['no_resident_demand'] and unknown['pressure'] is None, 'No demand state')
    conservation = {}
    for waste_type in WASTE_TYPES:
        points = snapshot['allocation'].points_by_type[waste_type]
        areas = [f['properties'] for f in snapshot['areas'] if f['properties']['waste_type'] == waste_type]
        residents = sum(p.residents for p in points)
        attributed = sum(a['attributed_capacity_m3'] or 0 for a in areas)
        check(isclose(residents, sum(a['residents'] or 0 for a in areas), abs_tol=1e-6), 'Resident conservation')
        check(isclose(attributed, sum(p.capacity for p in points if p.residents > 0), abs_tol=1e-6), 'Capacity conservation')
        conservation[waste_type] = {'residents': residents, 'attributed_capacity_m3': attributed,
            'points': len(points), 'zero_demand_points': sum(p.residents == 0 for p in points),
            'max_pressure': max(p.residents / p.capacity for p in points),
            'max_access_m': max(a['distance_m'] or 0 for a in areas)}
        conservation[waste_type]['highest_pressure_points'] = [
            {'point_id': p.min_bin_id, 'residents': p.residents, 'capacity_m3': p.capacity, 'pressure': p.residents / p.capacity}
            for p in sorted(points, key=lambda p: p.residents / p.capacity, reverse=True)[:5]]
    with (directory / 'bin_population.csv').open(encoding='utf-8-sig', newline='') as stream:
        for row in csv.DictReader(stream):
            check(isclose(float(row['resident_factor']), snapshot['allocation'].factor_by_bin[int(row['bin_id'])], abs_tol=1e-7), 'Existing allocation changed')
    estimates, prior = fit_assessments({1: Assessments(10, 0, 7, {1}), 2: Assessments(10, 10, 7, {2}),
                                       3: Assessments(1, 1, 1, {3}), 4: Assessments()}, {1: 1, 2: 1, 3: 4, 4: 1}, policy)
    check(prior['converged'] and 4 not in estimates and not estimates[3]['sufficient_evidence'], 'Sparse/no-assessment handling')
    check(all(0 <= x['interval_low'] <= x['interval_high'] <= 1 for x in estimates.values()), 'Posterior domains')
    with tempfile.TemporaryDirectory(dir=directory) as temporary:
        scratch = Path(temporary)
        identity = next(iter(snapshot['bin_to_point']))
        original = registry[identity]
        csv_path = scratch / 'daily.csv'
        fields = ['bin_id', 'date', 'waste_type', 'capacity_m3', 'object_group', 'site_id', 'fill_level']
        def write(labels):
            with csv_path.open('w', encoding='utf-8', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                for day, label in labels:
                    writer.writerow({**{k: original[k] for k in fields if k in original},
                                     'bin_id': identity, 'date': f'2026-06-{day:02d}', 'fill_level': label})
        write([(1, 'NULL'), (2, '3'), (3, '4'), (4, '')])
        item = next(iter(aggregate_daily(csv_path, registry, snapshot['bin_to_point'])['counts'].values()))
        check(item.total == 2 and item.level4 == 1, 'NULL/level-4 counting')
        write([(1, '4'), (1, '0')])
        expect_failure(lambda: aggregate_daily(csv_path, registry, snapshot['bin_to_point']))
        write([(1, '5')])
        expect_failure(lambda: aggregate_daily(csv_path, registry, snapshot['bin_to_point']))
        check(list_analyses(scratch) == {'analyses': []}, 'Empty catalog')
        expect_failure(lambda: get_analysis(scratch, '../../outside'))
    catalog = list_analyses(output_directory(directory))['analyses']
    documents = [get_analysis(output_directory(directory), entry['id'])[0] for entry in catalog]
    check(bool(documents), 'Generate artifacts before auditing')
    check(all(d['analysis']['pressure_thresholds'] == snapshot['thresholds'] for d in documents), 'Monthly thresholds drifted')
    for doc in documents:
        validate_artifact(doc)
        for waste_type in WASTE_TYPES:
            unique = {f['properties']['point_id']: f['properties'] for f in doc['features']
                      if f['properties']['waste_type'] == waste_type and f['properties']['point_id'] is not None}
            # Evidence at zero-demand points belongs to quality, not displayed area totals.
            check(sum(p['assessments'] for p in unique.values()) <= doc['analysis']['quality']['point_summaries'][waste_type]['assessments'], 'Duplicated point summary')
    with tempfile.TemporaryDirectory(dir=directory) as temporary:
        scratch = Path(temporary)
        doc = documents[0]
        path, _ = publish(doc, scratch)
        before = file_hash(path)
        check(publish(doc, scratch)[1] == 'reused' and file_hash(path) == before, 'Reuse changes bytes')
        changed = deepcopy(doc)
        changed['analysis']['input_fingerprint'] = '0' * 64
        expect_failure(lambda: publish(changed, scratch))
        check(file_hash(path) == before, 'Refusal changed result')
        publish(changed, scratch, True)
        check(list_analyses(scratch)['analyses'][0]['revision'] != before, 'Revision not refreshed')
        revision = file_hash(path)
        broken = deepcopy(changed)
        broken['features'][0]['properties']['assessments'] = -1
        expect_failure(lambda: publish(broken, scratch, True))
        check(file_hash(path) == revision, 'Failed publication replaced valid result')
        (scratch / 'ignored.geojson.tmp').write_text('bad')
        check(len(list_analyses(scratch)['analyses']) == 1, 'Temporary file discovered')
        (scratch / 'adequacy_2026-01.geojson').write_text('{}')
        expect_failure(lambda: list_analyses(scratch))
    report = {'checks': 'passed', 'conservation': conservation, 'thresholds': snapshot['thresholds'],
              'eligible_bins': len(snapshot['bin_to_point']), 'excluded_bins': len(bins) - len(snapshot['bin_to_point']),
              'months': [d['analysis']['month'] for d in documents], 'artifacts': catalog}
    if sensitivity:
        variants = [('pressure_75', replace(policy, pressure_quantile=.75)), ('pressure_90', replace(policy, pressure_quantile=.9)),
                    ('access_200', replace(policy, access_distance_m=200)), ('access_500', replace(policy, access_distance_m=500)),
                    ('evidence_loose', replace(policy, min_assessments=3, min_assessed_days=2, min_bin_coverage=.25, exceedance_probability=.8)),
                    ('evidence_strict', replace(policy, min_assessments=10, min_assessed_days=5, min_bin_coverage=.75, exceedance_probability=.95))]
        report['sensitivity'] = {}
        for name, variant in variants:
            reference = build_snapshot(bins, directory / 'population_density_1ha.geojson', variant)['thresholds']
            comparisons = {}
            for doc in documents:
                changed_residents, changed_points, categories = defaultdict(float), set(), Counter()
                for feature in doc['features']:
                    p = dict(feature['properties'])
                    w = p['waste_type']
                    p['high_pressure'] = p['pressure'] is not None and p['pressure'] >= reference[w]
                    p['sufficient_evidence'] = (p['assessments'] >= variant.min_assessments and p['assessed_days'] >= variant.min_assessed_days
                                                and p['bin_coverage'] >= variant.min_bin_coverage)
                    category, _ = classify(p, variant)
                    categories[category] += 1
                    if category != feature['properties']['category']:
                        changed_residents[w] += p['residents'] or 0
                        changed_points.add((w, p['point_id']))
                comparisons[doc['analysis']['month']] = {'changed_residents_by_type': dict(changed_residents),
                    'changed_point_types': len(changed_points), 'category_counts': dict(categories)}
            report['sensitivity'][name] = comparisons
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, required=True)
    parser.add_argument('--sensitivity', action='store_true')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    result = audit(args.data_dir, args.sensitivity)
    content = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)
    if args.report:
        args.report.write_text(content + '\n', encoding='utf-8')
    print(content)
