"""Fixed SQLAlchemy analytical queries; all scope and query choices are validated."""
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import and_, case, func, literal, select

from .contracts import ToolQueryError

from app.infrastructure.models import (
    Bin, Site, BinHist, ResidentRequest, BinSchedule, BinPopulation, BinDay,
    PopulationCell, CollectionStop, StopBin, Landfill, Truck,
)


def point_scope(model, ctx):
    b = ctx.bbox
    return and_(model.latitude >= b.min_latitude, model.latitude <= b.max_latitude,
                model.longitude >= b.min_longitude, model.longitude <= b.max_longitude)


def bins_scope(ctx, scope='area'):
    if ctx.selection_ids is not None and scope != 'global':
        return and_(point_scope(Bin, ctx), Bin.id.in_(ctx.selection_ids))
    return point_scope(Bin, ctx) if scope != 'global' else and_(Bin.latitude.between(-90, 90), Bin.longitude.between(-180, 180))


def period_filter(column, ctx, args, future=False, calendar=False):
    p = ctx.period(getattr(args, 'period', None), future=future)
    start = datetime.fromisoformat(p.start) if p.start else None
    end = datetime.fromisoformat(p.end)
    if calendar:
        start = start.date() if start else None
        end = datetime.fromisoformat(p.date_end_exclusive).date()
    return and_(*([column >= start] if start is not None else []), column < end)


def known_capacity():
    # PostgreSQL numeric special values must not enter capacity sums/means.
    return case((Bin.capacity_m3.not_in([Decimal('NaN'), Decimal('Infinity'), Decimal('-Infinity')]), Bin.capacity_m3), else_=None)


def capacity_columns():
    c = known_capacity()
    return [func.count().label('bins'), func.count(c).label('known_capacity_bins'),
            func.sum(c).label('total_known_capacity_m3'), func.avg(c).label('mean_known_capacity_m3'),
            func.count().filter(Bin.capacity_m3.is_(None)).label('missing_capacity_bins'),
            func.count().filter(and_(Bin.capacity_m3.is_not(None), c.is_(None))).label('invalid_capacity_bins')]


def grouping(args):
    name = getattr(args, 'grouping', None) or 'none'
    return literal('all') if name == 'none' else getattr(Bin, name)


def page(session, query, args, key='records'):
    limit, offset = getattr(args, 'limit', None) or 50, getattr(args, 'offset', None) or 0
    rows = [dict(row) for row in session.execute(query.offset(offset).limit(limit + 1)).mappings()]
    more = len(rows) > limit
    return {key: rows[:limit], 'returned_count': min(len(rows), limit), 'limit': limit, 'offset': offset,
            'has_more': more, 'next_offset': offset + limit if more else None}


def entity(model):
    columns = list(model.__table__.c)
    if model is Bin:
        columns.append(case((Bin.capacity_m3.is_(None), 'missing'), (known_capacity().is_(None), 'invalid_source_value'), else_='known').label('capacity_quality'))
    return columns


def validate_bin(session, ctx, bin_id):
    if not session.scalar(select(Bin.id).where(Bin.id == bin_id, point_scope(Bin, ctx))):
        raise ValueError('Bin is missing or outside the selected area (use internal bin ID)')


def optional_bin(session, ctx, args):
    bin_id = getattr(args, 'bin_id', None)
    if bin_id is not None:
        validate_bin(session, ctx, bin_id)
    return Bin.id == bin_id if bin_id is not None else literal(True)


def bin_summary(session, ctx, args):
    group = grouping(args)
    query = select(group.label('group'), *capacity_columns()).where(bins_scope(ctx, args.scope)).order_by(group.asc().nulls_first())
    if getattr(args, 'grouping', None) not in (None, 'none'):
        query = query.group_by(group)
    return page(session, query, args, 'groups')


def area_overview(session, ctx, args):
    from .contracts import Activity, Summary
    scope = point_scope(Bin, ctx)
    counts = dict(session.execute(select(*capacity_columns(), func.count(func.distinct(Bin.site_id)).label('represented_sites')).where(scope)).mappings().one())
    counts['location_sites'] = session.scalar(select(func.count()).select_from(Site).where(point_scope(Site, ctx)))
    counts['waste_types'] = bin_summary(session, ctx, Summary(grouping='waste_type'))
    counts['recent_service'] = service_summary(session, ctx, Activity())
    counts['recent_requests'] = request_summary(session, ctx, Activity())
    coverage = {}
    for model, column in [(BinHist, BinHist.date), (ResidentRequest, ResidentRequest.timestamp), (BinSchedule, BinSchedule.date), (BinDay, BinDay.date), (BinPopulation, None), (StopBin, None)]:
        query = select(func.count().label('rows'), func.count(func.distinct(model.bin_id)).label('bins'))
        if column is not None:
            query = query.add_columns(func.min(column).label('earliest'), func.max(column).label('latest'))
        query = query.select_from(model).join(Bin, Bin.id == model.bin_id).where(scope)
        coverage[model.__tablename__] = dict(session.execute(query).mappings().one())
        coverage[model.__tablename__]['available'] = model is ResidentRequest or coverage[model.__tablename__]['rows'] > 0
    for model in (PopulationCell, Landfill, Truck):
        coverage[model.__tablename__] = {'global_rows': session.scalar(select(func.count()).select_from(model))}
    from .adequacy import overview as adequacy_overview
    coverage['container_adequacy_analyses'] = adequacy_overview(session, ctx)
    counts['coverage'] = coverage
    return counts


def get_bin(session, ctx, args):
    validate_bin(session, ctx, args.bin_id)
    row = dict(session.execute(select(*entity(Bin)).where(Bin.id == args.bin_id)).mappings().one())
    row['evidence_counts'] = {model.__tablename__: session.scalar(select(func.count()).select_from(model).where(model.bin_id == args.bin_id)) for model in (BinHist, ResidentRequest, BinSchedule, BinPopulation)}
    return {'bin': row}


def bins_by_ids(session, ctx, args):
    records = [dict(row) for row in session.execute(select(*entity(Bin)).where(point_scope(Bin, ctx), Bin.id.in_(args.bin_ids)).order_by(Bin.id)).mappings()]
    found = {r['id'] for r in records}
    return {'records': records, 'missing_or_outside_ids': sorted(set(args.bin_ids) - found), 'returned_count': len(records)}


def bin_list(session, ctx, args):
    latest = select(BinHist.bin_id, func.max(BinHist.date).label('latest_attempt'), func.max(BinHist.date).filter(BinHist.was_serviced).label('latest_success')).where(BinHist.date < ctx.started_at.replace(tzinfo=None)).group_by(BinHist.bin_id).subquery()
    query = select(*entity(Bin), latest.c.latest_attempt, latest.c.latest_success, latest.c.latest_attempt.is_(None).label('unknown_history'), latest.c.latest_success.is_(None).label('unknown_successful_baseline')).outerjoin(latest, Bin.id == latest.c.bin_id).where(point_scope(Bin, ctx))
    for name in ('waste_type', 'waste_carrier', 'object_group'):
        value = getattr(args, name)
        if value is not None: query = query.where(getattr(Bin, name) == value)
    sort = args.sort or 'id'
    if sort == 'missing_history': query = query.where(latest.c.latest_attempt.is_(None))
    if sort == 'recently_serviced': query = query.where(latest.c.latest_success.is_not(None))
    if sort == 'not_serviced_since':
        if args.cutoff > ctx.started_at.date(): raise ToolQueryError('future_observation', 'Service cutoffs cannot be in the future.')
        query = query.where((latest.c.latest_success < datetime.combine(args.cutoff, datetime.min.time())) | latest.c.latest_success.is_(None))
    order = known_capacity().desc().nulls_last() if sort == 'largest_capacity' else latest.c.latest_success.desc().nulls_last() if sort == 'recently_serviced' else Bin.id
    return page(session, query.order_by(order, Bin.id), args)


def get_site(session, ctx, args):
    selected = session.scalar(select(func.count()).select_from(Bin).where(Bin.site_id == args.site_id, point_scope(Bin, ctx)))
    query = select(*entity(Site)).where(Site.id == args.site_id)
    row = session.execute(query).mappings().first()
    if not row or (not selected and not session.scalar(select(Site.id).where(Site.id == args.site_id, point_scope(Site, ctx)))):
        raise ValueError('Site is missing or outside selected location/member scopes')
    return {'site': dict(row), 'selected_member_bins': selected, 'whole_site_bins': session.scalar(select(func.count()).select_from(Bin).where(Bin.site_id == args.site_id)), 'scope_basis': 'Whole-site identity; member totals distinguish selected and all bins.'}


def site_list(session, ctx, args):
    return page(session, select(*entity(Site)).where(point_scope(Site, ctx)).order_by(Site.id), args)


def site_summary(session, ctx, args):
    group = grouping(args)
    query = select(Bin.site_id, group.label('group'), *capacity_columns()).where(point_scope(Bin, ctx)).group_by(Bin.site_id, group)
    if args.site_id is not None:
        get_site(session, ctx, args)
        query = query.where(Bin.site_id == args.site_id)
    order = func.count().desc() if args.sort == 'count' else func.sum(known_capacity()).desc().nulls_last() if args.sort == 'capacity' else Bin.site_id
    return {**page(session, query.order_by(order, Bin.site_id, group.asc().nulls_first()), args, 'groups'), 'scope_basis': 'Selected member-bin locations; not all bins of represented sites.'}


def event_query(session, ctx, args, model, column, future=False, calendar=False):
    constraint = optional_bin(session, ctx, args)
    return select(*entity(model)).select_from(model).join(Bin, Bin.id == model.bin_id).where(bins_scope(ctx, getattr(args, 'scope', None)), constraint, period_filter(column, ctx, args, future, calendar))


def service_history(session, ctx, args):
    return page(session, event_query(session, ctx, args, BinHist, BinHist.date).order_by(BinHist.date.desc(), BinHist.id.desc()), args)


def service_columns():
    count = func.count()
    successes = func.count().filter(BinHist.was_serviced)
    return [count.label('attempts'), successes.label('successes'), func.count().filter(~BinHist.was_serviced).label('failures'), successes.label('success_numerator'), count.label('success_denominator'), (successes * 1.0 / func.nullif(count, 0)).label('success_rate'), func.max(BinHist.date).label('latest_attempt'), func.max(BinHist.date).filter(BinHist.was_serviced).label('latest_success'), func.count(func.distinct(BinHist.bin_id)).label('bins_with_attempts')]


def service_summary(session, ctx, args):
    group = grouping(args)
    constraint = optional_bin(session, ctx, args)
    query = select(group.label('group'), *service_columns()).select_from(BinHist).join(Bin, Bin.id == BinHist.bin_id).where(bins_scope(ctx, args.scope), constraint, period_filter(BinHist.date, ctx, args)).order_by(group.asc().nulls_first())
    if args.grouping not in (None, 'none'): query = query.group_by(group)
    data = page(session, query, args, 'groups')
    data['eligible_bins'] = session.scalar(select(func.count()).select_from(Bin).where(bins_scope(ctx, args.scope), constraint))
    return data


def failure_reasons(session, ctx, args):
    group = grouping(args)
    query = select(group.label('group'), BinHist.non_serviced_reason.label('reason'), func.count().label('failed_attempts')).select_from(BinHist).join(Bin, Bin.id == BinHist.bin_id).where(bins_scope(ctx, args.scope), optional_bin(session, ctx, args), ~BinHist.was_serviced, period_filter(BinHist.date, ctx, args)).group_by(group, BinHist.non_serviced_reason).order_by(func.count().desc(), group.asc().nulls_first(), BinHist.non_serviced_reason.asc().nulls_first())
    return page(session, query, args, 'groups')


def fill_columns():
    return [func.count().label('attempts'), func.count(BinHist.fill_level).label('observed'), func.count().filter(BinHist.fill_level.is_(None)).label('missing'), func.avg(BinHist.fill_level).label('ordinal_category_mean'), *[func.count().filter(BinHist.fill_level == level).label('category_' + str(level)) for level in range(5)]]


def fill_summary(session, ctx, args):
    group = grouping(args)
    query = select(group.label('group'), *fill_columns()).select_from(BinHist).join(Bin, Bin.id == BinHist.bin_id).where(bins_scope(ctx, args.scope), optional_bin(session, ctx, args), period_filter(BinHist.date, ctx, args)).order_by(group.asc().nulls_first())
    if getattr(args, 'grouping', None) not in (None, 'none'):
        query = query.group_by(group)
    return page(session, query, args, 'groups')


def failed_attempts(session, ctx, args):
    return page(session, event_query(session, ctx, args, BinHist, BinHist.date).where(~BinHist.was_serviced).order_by(BinHist.date.desc(), BinHist.id.desc()), args)


def request_summary(session, ctx, args):
    group = grouping(args)
    constraint = optional_bin(session, ctx, args)
    query = select(group.label('group'), func.count().label('submissions'), func.count(func.distinct(ResidentRequest.bin_id)).label('reporting_bins')).select_from(ResidentRequest).join(Bin, Bin.id == ResidentRequest.bin_id).where(bins_scope(ctx, args.scope), constraint, period_filter(ResidentRequest.timestamp, ctx, args)).order_by(func.count().desc(), group.asc().nulls_first())
    if args.grouping not in (None, 'none'): query = query.group_by(group)
    return {**page(session, query, args, 'groups'), 'eligible_bins': session.scalar(select(func.count()).select_from(Bin).where(bins_scope(ctx, args.scope), constraint))}


def request_events(session, ctx, args):
    return page(session, event_query(session, ctx, args, ResidentRequest, ResidentRequest.timestamp).order_by(ResidentRequest.timestamp.desc(), ResidentRequest.id.desc()), args)


def requests_since_success(session, ctx, args):
    validate_bin(session, ctx, args.bin_id)
    end = ctx.started_at.replace(tzinfo=None)
    baseline = session.scalar(select(func.max(BinHist.date)).where(BinHist.bin_id == args.bin_id, BinHist.was_serviced, BinHist.date < end))
    total = session.scalar(select(func.count()).select_from(ResidentRequest).where(ResidentRequest.bin_id == args.bin_id, ResidentRequest.timestamp < end))
    subsequent = session.scalar(select(func.count()).select_from(ResidentRequest).where(ResidentRequest.bin_id == args.bin_id, ResidentRequest.timestamp > baseline, ResidentRequest.timestamp < end)) if baseline else None
    return {'bin_id': args.bin_id, 'latest_successful_service': baseline, 'baseline_known': baseline is not None, 'submissions_since_success': subsequent, 'total_submissions': total}


def trend(session, ctx, args, requests=False, synthetic=False):
    model = ResidentRequest if requests else BinDay if synthetic else BinHist
    column = ResidentRequest.timestamp if requests else model.date
    interval = args.interval or 'day'
    bucket = func.date_trunc(interval, column)
    scope = bins_scope(ctx, getattr(args, 'scope', None))
    filt = period_filter(column, ctx, args, calendar=synthetic)
    constraint = optional_bin(session, ctx, args)
    bounds = session.execute(select(func.min(column), func.max(column)).select_from(model).join(Bin, Bin.id == model.bin_id).where(scope, constraint, filt)).one()
    p = ctx.period(getattr(args, 'period', None))
    if p.start is not None or bounds[0] is not None:
        first = datetime.fromisoformat(p.start) if p.start else (bounds[0] if isinstance(bounds[0], datetime) else datetime.combine(bounds[0], datetime.min.time()))
        last = datetime.fromisoformat(p.date_end_exclusive) if synthetic else datetime.fromisoformat(p.end)
        last -= timedelta(microseconds=1)
        if interval == 'day': count = (last.date() - first.date()).days + 1
        elif interval == 'week': count = ((last.date() - first.date()).days + first.weekday()) // 7 + 1
        else: count = (last.year - first.year) * 12 + last.month - first.month + 1
        if count > 366: raise ToolQueryError('bucket_limit', 'More than 366 buckets; narrow the period or use week/month.')
    if requests: columns = [func.count().label('submissions'), func.count(func.distinct(model.bin_id)).label('reporting_bins')]
    elif synthetic: columns = synthetic_columns()
    else: columns = fill_columns() if args.metric == 'fill' else service_columns()
    query = select(bucket.label('bucket_start'), *columns).select_from(model).join(Bin, Bin.id == model.bin_id).where(scope, constraint, filt).group_by(bucket).order_by(bucket).limit(367)
    rows = [dict(r) for r in session.execute(query).mappings()]
    if len(rows) > 366: raise ToolQueryError('bucket_limit', 'More than 366 buckets; narrow the period or use week/month.')
    return {'buckets': rows, 'interval': interval, 'week_basis': 'ISO Monday start, identified by full date', 'gaps': 'Absent buckets have no recorded rows; no missing observation is imputed.', 'returned_count': len(rows)}


def activity_subqueries(ctx, args):
    h = select(BinHist.bin_id, func.count().label('attempts'), func.count().filter(BinHist.was_serviced).label('successes'), func.count().filter(~BinHist.was_serviced).label('failures'), func.max(BinHist.date).filter(BinHist.was_serviced).label('latest_success')).where(period_filter(BinHist.date, ctx, args)).group_by(BinHist.bin_id).subquery()
    r = select(ResidentRequest.bin_id, func.count().label('submissions')).where(period_filter(ResidentRequest.timestamp, ctx, args)).group_by(ResidentRequest.bin_id).subquery()
    return h, r


def activity_ranking(session, ctx, args):
    h, r = activity_subqueries(ctx, args)
    attempts, successes, failures, requests = [func.coalesce(c, 0) for c in (h.c.attempts, h.c.successes, h.c.failures, r.c.submissions)]
    query = select(Bin.id.label('bin_id'), Bin.site_id, Bin.waste_type, Bin.waste_carrier, attempts.label('attempts'), successes.label('successes'), failures.label('failures'), requests.label('submissions'), h.c.latest_success, h.c.attempts.is_(None).label('missing_period_history')).outerjoin(h, Bin.id == h.c.bin_id).outerjoin(r, Bin.id == r.c.bin_id).where(point_scope(Bin, ctx))
    order = [failures.desc(), attempts.desc()] if args.rank == 'high_failures' else [requests.desc(), successes.asc()]
    return page(session, query.order_by(*order, Bin.id), args)


def site_activity(session, ctx, args):
    h, r = activity_subqueries(ctx, args)
    query = select(Bin.site_id, func.count().label('selected_bins'), *[func.sum(func.coalesce(c, 0)).label(name) for c, name in ((h.c.attempts, 'attempts'), (h.c.successes, 'successes'), (h.c.failures, 'failures'), (r.c.submissions, 'submissions'))]).outerjoin(h, Bin.id == h.c.bin_id).outerjoin(r, Bin.id == r.c.bin_id).where(point_scope(Bin, ctx)).group_by(Bin.site_id)
    if args.site_id is not None:
        get_site(session, ctx, args)
        query = query.where(Bin.site_id == args.site_id)
    return page(session, query.order_by(Bin.site_id), args, 'groups')


def schedule_summary(session, ctx, args):
    query = event_query(session, ctx, args, BinSchedule, BinSchedule.date, future=True, calendar=True).subquery()
    return dict(session.execute(select(func.count().label('planned_dates'), func.count(func.distinct(query.c.bin_id)).label('scheduled_bins'), func.min(query.c.date).label('earliest'), func.max(query.c.date).label('latest')).select_from(query)).mappings().one())


def schedule_list(session, ctx, args):
    return page(session, event_query(session, ctx, args, BinSchedule, BinSchedule.date, future=True, calendar=True).order_by(BinSchedule.date, BinSchedule.id), args)


def synthetic_columns():
    return [func.count().label('synthetic_rows'), func.count(func.distinct(BinDay.bin_id)).label('distinct_bins'), *[func.count().filter(BinDay.collection_status == status).label(status) for status in ('none', 'collected', 'retry_collected', 'failed', 'missed')]]


def synthetic_summary(session, ctx, args):
    group = BinDay.collection_status if args.grouping == 'collection_status' else BinDay.waste_type if args.grouping == 'waste_type' else literal('all')
    query = select(group.label('group'), *synthetic_columns()).select_from(BinDay).join(Bin, Bin.id == BinDay.bin_id).where(point_scope(Bin, ctx), period_filter(BinDay.date, ctx, args, calendar=True)).order_by(group.asc().nulls_first())
    if getattr(args, 'grouping', None) not in (None, 'none'):
        query = query.group_by(group)
    return {**page(session, query, args, 'groups'), 'stored_global_rows': session.scalar(select(func.count()).select_from(BinDay)), 'coverage_note': 'No matching synthetic rows does not establish actual service outcomes.'}


def plan_query(ctx, args):
    return select(StopBin.stop_id, StopBin.bin_id, StopBin.predicted_fill, StopBin.due, Bin.capacity_m3.label('current_capacity_m3'), CollectionStop.date, CollectionStop.waste_carrier, CollectionStop.overall_volume_m3.label('whole_stop_snapshot_volume_m3'), CollectionStop.overall_predicted_fill_m3.label('whole_stop_predicted_fill_m3')).select_from(StopBin).join(Bin, Bin.id == StopBin.bin_id).join(CollectionStop, CollectionStop.id == StopBin.stop_id).where(point_scope(Bin, ctx), period_filter(CollectionStop.date, ctx, args, future=True, calendar=True))


def plan_list(session, ctx, args):
    return page(session, plan_query(ctx, args).order_by(CollectionStop.date, StopBin.stop_id, StopBin.bin_id), args)


def plan_summary(session, ctx, args):
    entries = plan_query(ctx, args).subquery()
    group = entries.c.waste_carrier if args.grouping == 'waste_carrier' else literal('all')
    capacity = case((entries.c.current_capacity_m3.not_in([Decimal('NaN'), Decimal('Infinity'), Decimal('-Infinity')]), entries.c.current_capacity_m3), else_=None)
    query = select(group.label('group'), func.count().label('selected_entries'), func.count(func.distinct(entries.c.stop_id)).label('represented_stops'), func.sum(capacity).label('selected_current_capacity_m3'), *[func.count().filter(entries.c.predicted_fill == level).label('predicted_category_' + str(level)) for level in range(5)]).order_by(group.asc().nulls_first())
    if args.grouping not in (None, 'none'): query = query.group_by(group)
    stops = select(entries.c.stop_id, entries.c.whole_stop_snapshot_volume_m3, entries.c.whole_stop_predicted_fill_m3).distinct().subquery()
    whole = dict(session.execute(select(func.sum(stops.c.whole_stop_snapshot_volume_m3).label('whole_stop_snapshot_volume_m3'), func.sum(stops.c.whole_stop_predicted_fill_m3).label('whole_stop_predicted_fill_m3'))).mappings().one())
    return {**page(session, query, args, 'groups'), 'stored_global_entries': session.scalar(select(func.count()).select_from(StopBin)), 'represented_whole_stop_context': whole, 'snapshot_scope': 'Whole-stop totals counted once per represented stop, including outside-area bins; current selected capacities are separate.'}


def facility_detail(session, ctx, args):
    row = session.execute(select(*entity(Landfill)).where(Landfill.id == args.facility_id)).mappings().first()
    if not row: raise ValueError('Facility not found')
    return {'facility': dict(row), 'scope_basis': 'Contextual facility identity may be outside area.'}


def facility_list(session, ctx, args):
    return page(session, select(*entity(Landfill)).where(point_scope(Landfill, ctx)).order_by(Landfill.id), args)


def proximity(session, ctx, args):
    from math import radians, cos
    lat = args.latitude if args.latitude is not None else (ctx.bbox.min_latitude + ctx.bbox.max_latitude) / 2
    lon = args.longitude if args.longitude is not None else (ctx.bbox.min_longitude + ctx.bbox.max_longitude) / 2
    # Compute and sort in PostgreSQL; fetch only bounded nearest facilities.
    a = func.pow(func.sin(func.radians(Landfill.latitude - lat) / 2), 2) + cos(radians(lat)) * func.cos(func.radians(Landfill.latitude)) * func.pow(func.sin(func.radians(Landfill.longitude - lon) / 2), 2)
    distance = 6371008.8 * 2 * func.asin(func.sqrt(func.least(1.0, func.greatest(0.0, a))))
    query = select(*entity(Landfill), distance.label('distance_metres')).where(Landfill.latitude.between(-90, 90), Landfill.longitude.between(-180, 180)).order_by(distance, Landfill.id).limit(args.limit or 10)
    return {'reference': {'latitude': lat, 'longitude': lon}, 'records': [dict(r) for r in session.execute(query).mappings()], 'distance_basis': 'Haversine spherical straight-line distance to reference point; not road distance, travel time or carrier route.'}


def fleet_summary(session, ctx, args):
    query = select(func.count().label('stored_trucks'), func.count().filter(~Truck.deleted).label('active'), func.count().filter(and_(~Truck.deleted, Truck.available)).label('available'), func.count().filter(Truck.deleted).label('retired'), func.sum(Truck.max_volume_m3).filter(and_(~Truck.deleted, Truck.available)).label('available_volume_m3')).select_from(Truck)
    if args.waste_carrier is not None: query = query.where(Truck.waste_carrier == args.waste_carrier)
    return {**dict(session.execute(query).mappings().one()), 'scope_basis': 'Global fleet registry; no stored geographic fleet attribution or route claims.'}


def compare_global(session, ctx, args):
    from .contracts import Activity, Summary
    data = {}
    for scope in ('area', 'global'):
        activity = Activity(scope=scope, grouping=args.grouping, period=args.period, limit=args.limit, offset=args.offset)
        data[scope] = {'registry': bin_summary(session, ctx, Summary(scope=scope, grouping=args.grouping, limit=args.limit, offset=args.offset)), 'service': service_summary(session, ctx, activity), 'requests': request_summary(session, ctx, activity)}
        denominator = data[scope]['service']['eligible_bins']
        data[scope]['eligible_bins'] = denominator
        # Scalar totals supply valid normalized intensity even when groups are paginated.
        total = request_summary(session, ctx, Activity(scope=scope, period=args.period))['groups']
        numerator = total[0]['submissions'] if total else 0
        data[scope]['request_intensity'] = {'numerator': numerator, 'denominator': denominator, 'submissions_per_bin': numerator / denominator if denominator else None}
    data['baseline'] = 'Global includes selected area and all eligible stored bins; not an area-excluding control group or municipal census.'
    return data
