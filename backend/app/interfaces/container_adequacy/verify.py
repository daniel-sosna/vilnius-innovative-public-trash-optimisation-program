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
from types import SimpleNamespace
import subprocess
import sys

from app.services.container_adequacy import (
    Assessments, Policy, WASTE_TYPES, aggregate_daily, aggregate_september, september_prefixes, build_snapshot, classify,
    file_hash, fit_assessments, latest_export, load_registry, make_document, publish,
)
from app.services.adequacy_artifacts import get_analysis, list_analyses, output_directory, validate_artifact, fingerprint
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


def artifact_audit(include_documents=False) -> dict:
    """Contract checks use a tiny declared fixture, without development sources."""
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)
        population = directory / 'population.geojson'
        ring = [[25.0,54.7],[25.001,54.7],[25.001,54.701],[25.0,54.701],[25.0,54.7]]
        population.write_text(json.dumps({'type': 'FeatureCollection', 'features': [
            {'type': 'Feature', 'properties': {'OBJECTID': 1, 'Shape_Area': 10000, 'gyv_sk_1ha': '100'},
             'geometry': {'type': 'Polygon', 'coordinates': [ring]}}]}))
        policy = Policy()
        snapshot = build_snapshot([BinRecord(i, w, 3, 54.7005, 25.0005, 'Daugiabučiai namai')
                                   for i, w in enumerate(WASTE_TYPES, 1)], population, policy)
        daily = {'complete_months': ['2026-09'], 'counts': {}, 'excluded_bins': [],
                 'coverage': {'2026-09': {'complete': True}}}
        legacy = make_document(snapshot, daily, '2026-09', {'fixture': 'a'*64}, policy)
        validate_artifact(legacy)
        documents = []
        for day in (1, 18, 30):
            doc = deepcopy(legacy)
            meta = doc['analysis']
            end = f'2026-09-{day:02d}'
            meta.update(id=f'adequacy-{end}', period_end=end, complete=day == 30,
                        schema_version='2', method_version='2',
                        static_reference_fingerprint='b'*64, policy_fingerprint=fingerprint(meta['policy']))
            meta['quality']['calendar'] = {'complete': True, 'period_start': '2026-09-01', 'period_end': end,
                'cohort_bins': 3, 'bins_present': 3, 'bins_with_full_calendar': 3, 'calendar_rows': 3 * day}
            validate_artifact(doc)
            (directory / f'adequacy_{end}.geojson').write_text(json.dumps(doc))
            check(get_analysis(directory, meta['id'])[0] == doc, 'Dated discovery mismatch')
            documents.append(doc)
        mutations = [(('period_end',), '2026-09-31'), (('period_end',), '2026-10-01'),
                     (('id',), 'adequacy-2026-09-19'), (('complete',), True),
                     (('complete',), 'false'), (('quality', 'calendar', 'complete'), False),
                     (('quality', 'calendar', 'calendar_rows'), 1)]
        for keys, value in mutations:
            broken = deepcopy(documents[1]); target = broken['analysis']
            for key in keys[:-1]:
                target = target[key]
            target[keys[-1]] = value
            expect_failure(lambda: validate_artifact(broken))
        broken = deepcopy(documents[1])
        broken['features'][0]['properties']['smoothed_frequency'] = 2
        expect_failure(lambda: validate_artifact(broken))
        population.unlink()
        check(len(list_analyses(directory)['analyses']) == 3, 'Dated file discovery')
    if include_documents:
        return documents
    return {'artifact_checks': 'passed', 'legacy_version': '1', 'dated_days': [1,18,30], 'rejected_mutations': 8}


def prefix_audit() -> dict:
    documents = artifact_audit(include_documents=True)
    base = documents[0]
    policy = Policy()
    registry = {i: {'waste_type': w, 'capacity_m3': '3', 'object_group': 'Daugiabučiai namai', 'site_id': str(i)}
                for i, w in enumerate(WASTE_TYPES, 1)}
    registry.update({i+3: {**row, 'site_id': str(i+3)} for i, row in list(registry.items())})
    bin_to_point = {i: (row['waste_type'], i) for i, row in registry.items()}
    areas = deepcopy(base['features'])
    for feature in base['features']:
        copied = deepcopy(feature); copied['id'] += 10
        copied['properties']['population_cell_id'] += 1
        copied['properties']['point_id'] += 3
        areas.append(copied)
    snapshot = {'areas': areas, 'thresholds': base['analysis']['pressure_thresholds'],
                'allocation': SimpleNamespace(points_by_type={w: [SimpleNamespace(min_bin_id=point, bins=[point]) for point in (i, i+3)]
                    for i, w in enumerate(WASTE_TYPES, 1)})}
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)
        source = directory / 'daily.csv'
        fields = ['bin_id', 'date', 'waste_type', 'capacity_m3', 'object_group', 'site_id', 'fill_level']
        def write(future=False, missing=False, extra=False):
            with source.open('w', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
                for day in range(1, 31):
                    for identity, row in registry.items():
                        if missing and day == 18 and identity == 1:
                            continue
                        writer.writerow({**row, 'bin_id': identity, 'date': f'2026-09-{day:02d}',
                            'fill_level': 'NULL' if day < 3 else '4' if (future and day > 18) or day % (7 if identity <= 3 else 2) == 0 else '1'})
                if extra:
                    writer.writerow({**registry[1], 'bin_id': 7, 'date': '2026-09-02', 'fill_level': '1'})
        def generate():
            daily = aggregate_september(source, registry, bin_to_point)
            return [make_document(snapshot, prefix, '2026-09', {'daily_synthetic_fill': file_hash(source)}, policy, cutoff)
                    for cutoff, prefix in september_prefixes(daily)]
        write()
        original = generate()
        check(len({doc['analysis']['id'] for doc in original}) == 30, 'Cutoff identities')
        check(all(doc['analysis']['complete'] == (i == 30) for i, doc in enumerate(original, 1)), 'Completion flags')
        check(all(prior is None for prior in original[0]['analysis']['priors'].values()), 'Sparse first day')
        check(all(f['properties']['raw_frequency'] is None for f in original[0]['features']), 'Invented first-day frequency')
        legacy = deepcopy(base)
        legacy['analysis'].update(id='adequacy-2026-09', schema_version='1', method_version='1', period_end='2026-09-30', complete=True)
        outputs = directory / 'outputs'
        legacy_path, _ = publish(legacy, outputs)
        legacy_hash = file_hash(legacy_path)
        revisions = {}
        for doc in original:
            validate_artifact(doc)
            path, status = publish(doc, outputs)
            revisions[path.name] = file_hash(path)
        for doc in generate():
            path, status = publish(doc, outputs)
            check(status == 'reused' and revisions[path.name] == file_hash(path), 'Repeat bytes changed')
        check(file_hash(legacy_path) == legacy_hash, 'Legacy output changed')
        write(future=True)
        changed = generate()
        for old, new in zip(original[:18], changed[:18]):
            check(old['features'] == new['features'], 'Future leakage into metrics/categories/uncertainty')
            check(old['analysis']['priors'] == new['analysis']['priors'], 'Future leakage into fitted priors')
            check(old['analysis']['quality'] == new['analysis']['quality'], 'Future leakage into coverage/counts')
        path = outputs / 'adequacy_2026-09-18.geojson'
        before = file_hash(path)
        expect_failure(lambda: publish(changed[17], outputs))
        check(file_hash(path) == before, 'Refusal changed saved result')
        publish(changed[17], outputs, True)
        before = file_hash(path)
        broken = deepcopy(changed[17]); broken['features'][0]['properties']['assessments'] = -1
        expect_failure(lambda: publish(broken, outputs, True))
        check(file_hash(path) == before, 'Failed replacement changed result')
        write(missing=True)
        expect_failure(generate)
        write(extra=True)
        extra_registry = {**registry, 7: registry[1]}
        expect_failure(lambda: list(september_prefixes(aggregate_september(source, extra_registry, bin_to_point))))
        run = subprocess.run([sys.executable, '-m', 'app.interfaces.container_adequacy', '--month', '2026-09',
                              '--september-cutoffs', '--daily', str(source)], capture_output=True)
        check(run.returncode == 2, 'CLI period modes not exclusive')
    return {'prefix_checks': 'passed', 'cutoffs': 30, 'no_future_leakage_through_day': 18,
            'sparse_evidence': 'preserved', 'coverage_rejections': 2, 'repeat_bytes': 'identical',
            'legacy_file': 'unchanged', 'failed_publication': 'preserved', 'cli_exclusivity': 'passed'}


def audit(directory: Path, sensitivity: bool, daily_path: Path | None = None) -> dict:
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
    def saved_documents():
        return (get_analysis(output_directory(directory), entry['id'])[0] for entry in catalog)
    check(bool(catalog), 'Generate artifacts before auditing')
    check(all(d['analysis']['pressure_thresholds'] == snapshot['thresholds'] for d in saved_documents()), 'Monthly thresholds drifted')
    for doc in saved_documents():
        validate_artifact(doc)
        for waste_type in WASTE_TYPES:
            unique = {f['properties']['point_id']: f['properties'] for f in doc['features']
                      if f['properties']['waste_type'] == waste_type and f['properties']['point_id'] is not None}
            # Evidence at zero-demand points belongs to quality, not displayed area totals.
            check(sum(p['assessments'] for p in unique.values()) <= doc['analysis']['quality']['point_summaries'][waste_type]['assessments'], 'Duplicated point summary')
    with tempfile.TemporaryDirectory(dir=directory) as temporary:
        scratch = Path(temporary)
        doc = get_analysis(output_directory(directory), catalog[0]['id'])[0]
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
              'months': [entry['month'] for entry in catalog], 'artifacts': catalog}
    if daily_path is not None:
        source = aggregate_september(daily_path, registry, snapshot['bin_to_point'])
        dated = {entry['id']: entry for entry in catalog if entry['schema_version'] == '2'}
        check(len(dated) == 30, 'Expected all thirty real cutoffs')
        for cutoff, prefix in september_prefixes(source):
            doc = get_analysis(output_directory(directory), f'adequacy-{cutoff.isoformat()}')[0]
            check(doc['analysis']['quality']['calendar'] == prefix['coverage']['2026-09'], 'Source coverage differs')
            for feature in doc['features']:
                properties = feature['properties']
                item = prefix['counts'].get(('2026-09', properties['waste_type'], properties['point_id']), Assessments())
                check((properties['assessments'], properties['level4_count'], properties['assessed_days'], properties['assessed_bins'])
                      == (item.total, item.level4, item.days.bit_count(), len(item.bins)), 'Source prefix counts differ')
            if cutoff.day in (1, 18, 30):
                generated = make_document(snapshot, prefix, '2026-09', doc['analysis']['source_fingerprints'], policy, cutoff)
                check(generated == doc, 'Source refitting differs from saved cutoff')
        # Later labels can be changed without entering the captured prefix fitting.
        mutated = deepcopy(source)
        for (day, waste, point), item in mutated['day_counts'].items():
            if day > 18:
                item.level4 = item.total - item.level4
        for cutoff, prefix in september_prefixes(mutated):
            if cutoff.day == 18:
                saved = get_analysis(output_directory(directory), 'adequacy-2026-09-18')[0]
                meta = saved['analysis']
                generated = make_document(snapshot, prefix, '2026-09', meta['source_fingerprints'], policy, cutoff)
                check(generated == saved, 'Real future-label leakage')
                break
        report['source_prefix_audit'] = {'cutoffs': 30, 'refitted_days': [1,18,30], 'no_future_leakage': 'passed'}
    if sensitivity:
        variants = [('pressure_75', replace(policy, pressure_quantile=.75)), ('pressure_90', replace(policy, pressure_quantile=.9)),
                    ('access_200', replace(policy, access_distance_m=200)), ('access_500', replace(policy, access_distance_m=500)),
                    ('evidence_loose', replace(policy, min_assessments=3, min_assessed_days=2, min_bin_coverage=.25, exceedance_probability=.8)),
                    ('evidence_strict', replace(policy, min_assessments=10, min_assessed_days=5, min_bin_coverage=.75, exceedance_probability=.95))]
        report['sensitivity'] = {}
        for name, variant in variants:
            reference = build_snapshot(bins, directory / 'population_density_1ha.geojson', variant)['thresholds']
            comparisons = {}
            for doc in saved_documents():
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
    parser.add_argument('--data-dir', type=Path)
    parser.add_argument('--prefix-contracts', action='store_true', help='Audit all September prefixes and future-label independence')
    parser.add_argument('--artifact-contracts', action='store_true', help='Audit portable v1/v2 contracts using a tiny fixture')
    parser.add_argument('--daily', type=Path, help='Audit saved September prefixes against this explicit immutable source')
    parser.add_argument('--sensitivity', action='store_true')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    if not (args.artifact_contracts or args.prefix_contracts) and args.data_dir is None:
        parser.error('--data-dir is required unless --artifact-contracts is selected')
    result = prefix_audit() if args.prefix_contracts else artifact_audit() if args.artifact_contracts else audit(args.data_dir, args.sensitivity, args.daily)
    content = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)
    if args.report:
        args.report.write_text(content + '\n', encoding='utf-8')
    print(content)
