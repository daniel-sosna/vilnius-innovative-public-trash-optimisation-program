"""Read saved cutoff evidence in the trusted run area; never fit or publish data."""
from math import isfinite

from shapely.errors import ShapelyError
from shapely.geometry import box, shape
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.infrastructure.models import ContainerAdequacyAnalysis
from app.services.adequacy_artifacts import CATEGORIES, WASTE_TYPES
from .contracts import ToolQueryError


LIMITATIONS = [
    'Population totals include whole intersecting polygons, not residents clipped to the bbox.',
    'Each waste stream has a separate population allocation; stream totals are not unique residents.',
    'Serving-point evidence includes referenced points outside the bbox and counts each waste/point once.',
    'Point capacity is full serving-point capacity, not capacity physically inside the bbox.',
    'Saved categories are candidate signals, not proven shortage, observed causation or predicted overflow.',
]


def provenance(ctx):
    meta = ctx.adequacy_metadata
    return {'id': ctx.adequacy_id, 'revision': ctx.adequacy_revision,
            'project_date': ctx.project_date.isoformat(),
            'period_start': '2026-09-01', 'period_end': ctx.project_date.isoformat(),
            'end_inclusive': True, 'complete': meta['complete'] if meta else ctx.project_date.day == 30,
            **({key: meta[key] for key in ('schema_version', 'method_version', 'fill_provenance',
                                           'source_fingerprints', 'static_reference_fingerprint', 'policy_fingerprint',
                                           'policy', 'pressure_thresholds', 'assumptions')} if meta else {}),
            'source_calendar': meta['quality']['calendar'] if meta else None,
            'category_meanings': {
                'priority_shortage': 'Static pressure/access signal and elevated level-4 posterior with sufficient evidence.',
                'potential_shortage': 'Static pressure/access signal with sufficient evidence; no elevated level-4 signal.',
                'overflow_without_pressure': 'Elevated level-4 posterior without a static pressure/access signal.',
                'ordinary': 'Sufficient evidence with neither elevated signal.',
                'insufficient_evidence': 'Too few assessments/days/bin coverage for the saved policy.',
                'unavailable': 'Unknown population, no resident demand or no serving point.',
            },
            'population_scope': 'full intersecting-polygon estimates per waste stream',
            'capacity_scope': 'full referenced serving points, including external service context',
            'limitations': LIMITATIONS}


def _revision(session, ctx):
    if not ctx.adequacy_discovered:
        raise ToolQueryError('overview_required', 'Discover saved risk evidence with get_area_overview first.')
    if ctx.adequacy_discovery_error:
        raise ToolQueryError(ctx.adequacy_discovery_error, 'Saved risk discovery failed; start a new investigation to retry.')
    # Absence is pinned too: do not discover a newly imported cutoff mid-run.
    if ctx.adequacy_revision is None:
        return False
    revision = session.scalar(select(ContainerAdequacyAnalysis.revision).where(ContainerAdequacyAnalysis.id == ctx.adequacy_id))
    if revision != ctx.adequacy_revision:
        raise ToolQueryError('stale_evidence', 'Saved risk revision changed or disappeared; start a new investigation.')
    return True


def _matches(session, ctx):
    if not _revision(session, ctx):
        return []
    if ctx.adequacy_matches is not None:
        return ctx.adequacy_matches
    features = session.scalar(select(ContainerAdequacyAnalysis.features).where(
        ContainerAdequacyAnalysis.id == ctx.adequacy_id,
        ContainerAdequacyAnalysis.revision == ctx.adequacy_revision))
    if features is None:
        raise ToolQueryError('stale_evidence', 'Saved risk revision changed; start a new investigation.')
    b = ctx.bbox
    rectangle = box(b.min_longitude, b.min_latitude, b.max_longitude, b.max_latitude)
    matches, invalid = [], []
    for feature in features:
        if ctx.remaining(True) <= 0:
            raise TimeoutError('Saved risk spatial deadline')
        if not isinstance(feature, dict):
            invalid.append(None)
            continue
        try:
            geometry = shape(feature['geometry'])
            if geometry.geom_type not in ('Polygon', 'MultiPolygon') or geometry.is_empty or not geometry.is_valid:
                raise ValueError('Invalid saved polygon')
            if not all(isfinite(x) for x in geometry.bounds):
                raise ValueError('Nonfinite saved polygon')
            if geometry.intersects(rectangle):
                matches.append({'feature_id': feature['id'], **feature['properties']})
        except (ValueError, TypeError, KeyError, IndexError, AttributeError, ShapelyError):
            invalid.append(feature.get('id'))
    ctx.adequacy_matches = sorted(matches, key=lambda feature: feature['feature_id'])
    ctx.adequacy_geometry_coverage = {
        'matched_features': len(matches), 'invalid_geometry_features': len(invalid),
        'invalid_geometry_ids': invalid[:50], 'invalid_ids_omitted': max(0, len(invalid) - 50),
        'geometry_scope': 'exact bbox intersection, including boundaries and respecting holes',
        'geometry_limitation': 'Invalid polygons are excluded; zero matches cannot establish coverage for excluded geometry.' if invalid else None,
    }
    return ctx.adequacy_matches


def discover(session, ctx):
    if not ctx.adequacy_discovered:
        row = session.execute(select(ContainerAdequacyAnalysis.analysis, ContainerAdequacyAnalysis.revision).where(
            ContainerAdequacyAnalysis.id == ctx.adequacy_id)).one_or_none()
        ctx.adequacy_discovered = True
        if row is not None:
            ctx.adequacy_metadata, ctx.adequacy_revision = row
    matches = _matches(session, ctx)
    return {'available': ctx.adequacy_revision is not None,
            'code': None if ctx.adequacy_revision else 'missing_cutoff',
            'artifact': provenance(ctx), 'geometry_coverage': ctx.adequacy_geometry_coverage,
            'matched_features': len(matches)}


def overview(session, ctx):
    try:
        # Contain an optional saved-risk query failure without losing other overview evidence.
        with session.begin_nested():
            return discover(session, ctx)
    except SQLAlchemyError:
        ctx.adequacy_discovered = True
        ctx.adequacy_discovery_error = 'query_failed'
        return {'available': None, 'status': 'error', 'code': 'query_failed',
                'message': 'Saved adequacy read failed; this is not missing or zero evidence.',
                'id': ctx.adequacy_id, 'project_date': ctx.project_date.isoformat()}


def _base(session, ctx):
    features = _matches(session, ctx)
    return features, {'available': ctx.adequacy_revision is not None,
                      'code': None if ctx.adequacy_revision else 'missing_cutoff',
                      'artifact': provenance(ctx), 'geometry_coverage': ctx.adequacy_geometry_coverage,
                      'units': {'capacity': 'assumed m³', 'pressure': 'estimated residents/m³',
                                'distance': 'straight-line metres', 'frequency': 'level-4 fraction of known assessments',
                                'uncertainty': '90% conditional beta posterior interval per serving point'}}


def _known_sum(values):
    known = [value for value in values if value is not None]
    return sum(known) if known else None


def _range(values):
    known = [value for value in values if value is not None]
    return {'min': min(known), 'max': max(known)} if known else None


def summary(session, ctx, args):
    features, data = _base(session, ctx)
    if not data['available']:
        return {**data, 'streams': []}
    streams = []
    for waste in WASTE_TYPES:
        if args.waste_type is not None and waste != args.waste_type:
            continue
        areas = [feature for feature in features if feature['waste_type'] == waste]
        points = {feature['point_id']: feature for feature in areas if feature['point_id'] is not None}
        evidence = list(points.values())
        count = sum(point['assessments'] for point in evidence)
        level4 = sum(point['level4_count'] for point in evidence)
        categories = []
        for category in sorted(CATEGORIES):
            members = [feature for feature in areas if feature['category'] == category]
            categories.append({'category': category, 'areas': len(members),
                               'known_population_areas': sum(feature['residents'] is not None for feature in members),
                               'missing_population_areas': sum(feature['residents'] is None for feature in members),
                               'full_polygon_residents': _known_sum(feature['residents'] for feature in members)})
        streams.append({'waste_type': waste, 'areas': len(areas), 'categories': categories,
                        'known_population_areas': sum(feature['residents'] is not None for feature in areas),
                        'missing_population_areas': sum(feature['residents'] is None for feature in areas),
                        'full_polygon_residents': _known_sum(feature['residents'] for feature in areas),
                        'unique_serving_points': len(points),
                        'serving_point_evidence': {
                            'deduplication_key': ['waste_type', 'point_id'],
                            'point_bins': sum(point['point_bin_count'] for point in evidence),
                            'known_capacity_points': sum(point['point_capacity_m3'] is not None for point in evidence),
                            'missing_capacity_points': sum(point['point_capacity_m3'] is None for point in evidence),
                            'full_point_capacity_m3': _known_sum(point['point_capacity_m3'] for point in evidence),
                            'assessments': count, 'level4_count': level4,
                            'raw_frequency': level4 / count if count else None,
                            'assessed_points': sum(point['assessments'] > 0 for point in evidence),
                            'sufficient_evidence_points': sum(point['sufficient_evidence'] for point in evidence),
                            'bin_coverage_range': _range(point['bin_coverage'] for point in evidence),
                            'smoothed_frequency_range': _range(point['smoothed_frequency'] for point in evidence),
                            'interval_low_range': _range(point['interval_low'] for point in evidence),
                            'interval_high_range': _range(point['interval_high'] for point in evidence),
                            'uncertainty_scope': 'ranges across unique serving points, not a pooled posterior',
                        }, 'fitted_prior': ctx.adequacy_metadata['priors'][waste],
                        'pressure_reference': ctx.adequacy_metadata['pressure_thresholds'][waste]})
    return {**data, 'streams': streams}


def listing(session, ctx, args):
    features, data = _base(session, ctx)
    selected = [feature for feature in features if (args.waste_type is None or feature['waste_type'] == args.waste_type)
                and (args.category is None or feature['category'] == args.category)]
    limit, offset = args.limit or 50, args.offset or 0
    records = selected[offset:offset + limit]
    more = offset + len(records) < len(selected)
    return {**data, 'records': records, 'total_matches': len(selected), 'returned_count': len(records),
            'limit': limit, 'offset': offset, 'has_more': more, 'next_offset': offset + len(records) if more else None}


def detail(session, ctx, args):
    features, data = _base(session, ctx)
    if not data['available']:
        return {**data, 'feature': None}
    feature = next((feature for feature in features if feature['feature_id'] == args.feature_id), None)
    if feature is None:
        raise ToolQueryError('invalid_feature', 'Feature is missing or outside the captured artifact/bbox.')
    waste = feature['waste_type']
    return {**data, 'feature': feature, 'pressure_reference': ctx.adequacy_metadata['pressure_thresholds'][waste],
            'fitted_prior': ctx.adequacy_metadata['priors'][waste]}
