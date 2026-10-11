"""Envelope-filtered exact spatial evidence, including holes/shared boundaries."""
from collections import defaultdict
from dataclasses import replace

from shapely.geometry import Point, Polygon, box, shape
from shapely.strtree import STRtree
from sqlalchemy import Float, cast, func, select, literal_column

from app.infrastructure.models import Bin, BinPopulation, DistrictBoundary, ServiceZone, PopulationCell
from . import queries as q
from .contracts import Activity, Bbox


class GeometryCandidates(list):
    def __init__(self):
        super().__init__()
        self.invalid_ids = []

    def coverage(self):
        return {'invalid_geometry_candidate_ids': self.invalid_ids,
                'invalid_geometry_candidates': len(self.invalid_ids),
                'geometry_limitation': 'Invalid polygons are unavailable and excluded. Unmatched means no valid covering geometry; excluded invalid polygons may conceal membership.' if self.invalid_ids else None}


def candidate_geometries(session, ctx, kind):
    b = ctx.bbox
    if kind == 'population':
        model = PopulationCell
        query = select(model).where(model.min_lon <= b.max_longitude, model.max_lon >= b.min_longitude, model.min_lat <= b.max_latitude, model.max_lat >= b.min_latitude).order_by(model.id)
    else:
        model = DistrictBoundary if kind == 'district' else ServiceZone
        # Derive candidate envelopes in PostgreSQL without requiring PostGIS.
        vertices = func.jsonb_path_query(model.geometry, literal_column("'$.coordinates[*][*]'::jsonpath")).table_valued('value').render_derived(name='vertex')
        x = cast(vertices.c.value.op('->>')(0), Float)
        y = cast(vertices.c.value.op('->>')(1), Float)
        minx = select(func.min(x)).select_from(vertices).correlate(model).scalar_subquery()
        maxx = select(func.max(x)).select_from(vertices).correlate(model).scalar_subquery()
        miny = select(func.min(y)).select_from(vertices).correlate(model).scalar_subquery()
        maxy = select(func.max(y)).select_from(vertices).correlate(model).scalar_subquery()
        query = select(model).where(minx <= b.max_longitude, maxx >= b.min_longitude, miny <= b.max_latitude, maxy >= b.min_latitude).order_by(model.id)
    rectangle = box(b.min_longitude, b.min_latitude, b.max_longitude, b.max_latitude)
    result = GeometryCandidates()
    for row in session.scalars(query):
        if ctx.remaining(True) <= 0: raise TimeoutError('Spatial deadline')
        geo = Polygon(row.geometry[0], row.geometry[1:]) if kind == 'population' else shape(row.geometry)
        if not geo.is_valid:
            result.invalid_ids.append(row.id)
            continue
        if geo.intersects(rectangle): result.append((row, geo))
    return result


def membership(session, ctx, candidates):
    tree = STRtree([geo for _, geo in candidates])
    query = select(Bin.id, Bin.site_id, Bin.waste_type, Bin.longitude, Bin.latitude, BinPopulation.population_cell_id.label('stored_population_cell_id'), BinPopulation.resident_factor).outerjoin(BinPopulation, BinPopulation.bin_id == Bin.id).where(q.bins_scope(ctx)).order_by(Bin.id).execution_options(yield_per=500)
    for row in session.execute(query).mappings():
        if ctx.remaining(True) <= 0: raise TimeoutError('Spatial deadline')
        point = Point(row['longitude'], row['latitude'])
        matches = sorted((candidates[int(index)][0] for index in tree.query(point) if candidates[int(index)][1].covers(point)), key=lambda value: value.id)
        yield dict(row), matches[0] if matches else None, len(matches)


def geographic_context(session, ctx, args):
    candidates = candidate_geometries(session, ctx, args.kind)
    counts = defaultdict(int)
    unmatched = ambiguous = selected = 0
    for row, polygon, matches in membership(session, ctx, candidates):
        selected += 1
        if polygon: counts[polygon.id] += 1
        else: unmatched += 1
        ambiguous += matches > 1
    records = [{'id': row.id, 'name': row.district_name if args.kind == 'district' else row.zone_name, 'selected_bin_count': counts[row.id]} for row, _ in candidates]
    offset, limit = args.offset or 0, args.limit or 50
    return {**candidates.coverage(), 'records': records[offset:offset + limit], 'selected_bins': selected, 'unmatched_bins': unmatched, 'ambiguous_bins': ambiguous, 'membership_rule': 'Boundary-inclusive covers; lowest stored ID wins multiple matches.', 'returned_count': len(records[offset:offset + limit]), 'limit': limit, 'offset': offset, 'has_more': len(records) > offset + limit, 'next_offset': offset + limit if len(records) > offset + limit else None}


def geographic_summary(session, ctx, args):
    model = DistrictBoundary if args.kind == 'district' else ServiceZone
    row = session.get(model, args.geographic_id)
    if row is None: raise ValueError('Geography not found')
    geo = shape(row.geometry)
    if not geo.is_valid:
        return {'available': False, 'reason': 'invalid_geometry', 'geographic_id': row.id, 'geometry_limitation': 'Stored invalid geometry is unavailable; no repair or inferred membership.'}
    minx, miny, maxx, maxy = geo.bounds
    whole_context = replace(ctx, bbox=Bbox(min_latitude=miny, min_longitude=minx, max_latitude=maxy, max_longitude=maxx))
    candidates = candidate_geometries(session, whole_context, args.kind)
    ids = [record['id'] for record, polygon, _ in membership(session, whole_context, candidates) if polygon is not None and polygon.id == args.geographic_id]
    selected_ids = [bin_id for bin_id in session.scalars(select(Bin.id).where(q.point_scope(Bin, ctx), Bin.id.in_(ids)))]
    result = {}
    for name, matching_ids, context in [('whole_geography', ids, whole_context), ('selected_intersection', selected_ids, ctx)]:
        scoped = replace(context, selection_ids=matching_ids)
        activity = Activity(period=args.period)
        result[name] = {'bins': len(matching_ids), 'service': q.service_summary(session, scoped, activity), 'requests': q.request_summary(session, scoped, activity)}
    return {**candidates.coverage(), **result, 'geographic_id': row.id, 'membership_rule': 'Lowest-ID boundary-inclusive membership across stored polygons; both summaries use the same period.'}


def density_band(cell):
    if cell is None or (cell.density_per_ha is None and not cell.suppressed): return 'unavailable'
    if cell.suppressed: return 'suppressed (assumed density)'
    d = cell.density_per_ha
    return '<11' if d < 11 else '11–49' if d < 50 else '50–99' if d < 100 else '100–199' if d < 200 else '200+'


def population_summary(session, ctx, args):
    candidates = candidate_geometries(session, ctx, 'population')
    groups = {}
    polygons = {}
    unmatched = ambiguous = missing_density = missing_allocation = selected = 0
    for record, cell, matches in membership(session, ctx, candidates):
        selected += 1
        ambiguous += matches > 1
        unmatched += cell is None
        missing_density += cell is None or (cell.density_per_ha is None and not cell.suppressed)
        missing_allocation += record['resident_factor'] is None
        key = record['waste_type'] if args.grouping == 'waste_type' else density_band(cell) if args.grouping == 'density_band' else cell.id if cell else None
        group = groups.setdefault(key, {'group': key, 'selected_bins': 0, 'source_polygon_ids': set(), 'stored_allocations_by_waste_type': {}})
        group['selected_bins'] += 1
        if cell:
            group['source_polygon_ids'].add(cell.id)
            polygons[cell.id] = cell
        if record['resident_factor'] is not None:
            waste = record['waste_type']
            group['stored_allocations_by_waste_type'][waste] = group['stored_allocations_by_waste_type'].get(waste, 0) + record['resident_factor']
    for group in groups.values():
        members = [polygons[id] for id in sorted(group['source_polygon_ids'])]
        known = [cell.residents for cell in members if cell.density_per_ha is not None or cell.suppressed]
        group['source_polygon_ids'] = sorted(group['source_polygon_ids'])
        group['full_source_polygon_residents'] = sum(known) if known else None
        group['unique_source_polygons'] = len(members)
    ordered = sorted(groups.values(), key=lambda value: str(value['group']))
    offset, limit = args.offset or 0, args.limit or 50
    known = [cell.residents for cell in polygons.values() if cell.density_per_ha is not None or cell.suppressed]
    return {**candidates.coverage(), 'groups': ordered[offset:offset + limit], 'selected_bins': selected, 'unique_source_polygons': len(polygons), 'full_source_polygon_residents': sum(known) if known else None, 'unmatched_bins': unmatched, 'ambiguous_bins': ambiguous, 'missing_density_bins': missing_density, 'missing_allocation_bins': missing_allocation, 'returned_count': len(ordered[offset:offset + limit]), 'limit': limit, 'offset': offset, 'has_more': len(ordered) > offset + limit, 'next_offset': offset + limit if len(ordered) > offset + limit else None, 'population_basis': 'Full source polygons counted once, not bbox population or unique bin customers. Group totals may overlap polygons; do not sum across groups. Stored allocations are per waste stream, not unique people.'}


def population_list(session, ctx, args):
    candidates = candidate_geometries(session, ctx, 'population')
    rows = []
    offset, limit = args.offset or 0, args.limit or 50
    for index, (record, cell, matches) in enumerate(membership(session, ctx, candidates)):
        if index < offset: continue
        if len(rows) > limit: break
        rows.append({**record, 'current_spatial_population_cell_id': cell.id if cell else None, 'density_per_ha': cell.density_per_ha if cell else None, 'density_band': density_band(cell), 'suppressed': cell.suppressed if cell else None, 'full_source_polygon_residents': cell.residents if cell and (cell.density_per_ha is not None or cell.suppressed) else None, 'ambiguous_membership': matches > 1})
    more = len(rows) > limit
    return {**candidates.coverage(), 'records': rows[:limit], 'returned_count': min(limit, len(rows)), 'limit': limit, 'offset': offset, 'has_more': more, 'next_offset': offset + limit if more else None, 'allocation_basis': 'Stored allocation and source cell may lag registry edits; current spatial membership is computed independently.'}
