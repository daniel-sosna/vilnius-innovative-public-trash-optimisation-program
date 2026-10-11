"""Single catalogue for local dispatch, strict provider schemas and documentation."""
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from functools import partial
import json
import logging
from math import isfinite
from time import monotonic
from typing import Callable

from pydantic import BaseModel, ValidationError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from . import contracts as c, queries as q, spatial as s
from .reads import analytical_session

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Tool:
    name: str
    inputs: type[BaseModel]
    query: Callable
    description: str
    evidence: str = 'recorded/current registry'
    future: bool = False
    result_type: type[c.Result] = c.Result


TOOLS = [
    Tool('get_area_overview', c.Empty, q.area_overview, 'Start here: compact selected-bin/site counts, known/missing/invalid source capacity, waste distribution, recent recorded activity and optional dataset/date coverage.'),
    Tool('get_bin', c.BinId, q.get_bin, 'Internal bin ID detail with site reference and evidence counts. Reject missing/outside-area identity; external_id is separate.'),
    Tool('get_bins_by_ids', c.BinIds, q.bins_by_ids, 'At most 100 internal bin IDs; selected records plus missing/outside IDs; never silently widen area.'),
    Tool('list_bins', c.BinList, q.bin_list, 'Selected bins with source-value filters and investigative sorts. latest_success differs from latest_attempt; missing history is unknown, not proven overdue. Cutoff required only for not_serviced_since.'),
    Tool('get_bin_summary', c.Summary, q.bin_summary, 'Area/global count and known-capacity totals/means, missing/invalid coverage grouped by current registry; NULL and source categories retained.'),
    Tool('get_site', c.SiteId, q.get_site, 'Site identity and distinct whole-site versus selected-member counts; own mean location may differ from member-bin locations.'),
    Tool('list_sites', c.Page, q.site_list, 'Deterministically paginated sites whose own stored locations are inside bbox; not sites merely represented by selected bins.'),
    Tool('get_site_summary', c.Sites, q.site_summary, 'Selected member-bin counts/capacity per site and optional waste/carrier breakdown, ranked by count/capacity; outside members excluded.'),
    Tool('get_bin_service_history', c.History, q.service_history, 'Raw recorded attempts for selected internal bin ID, timestamp/ID descending. Success/failure, NULL/empty reason and 0–3/NULL observed fill retained.'),
    Tool('get_service_summary', c.Activity, q.service_summary, 'Recorded attempts, successes, failures, latest attempt/success and coverage. Success rate returns successful/all-attempt numerator/denominator; zero denominator is NULL, never schedule completion.'),
    Tool('get_service_failure_reasons', c.Activity, q.failure_reasons, 'Failed recorded attempts grouped by exact reason plus current registry grouping; NULL and empty reasons remain distinct.'),
    Tool('get_fill_summary', c.Activity, q.fill_summary, 'Recorded fill category counts 0–3, observed/missing counts and explicitly ordinal mean (not percent/volume); all-NULL mean unavailable.'),
    Tool('get_service_trend', c.Trend, q.trend, 'Day/week/month recorded service/failure/fill metrics with valid denominators; full-date ISO Monday weeks. Maximum 366 effective buckets, gaps are not imputed.'),
    Tool('list_failed_service_attempts', c.Events, q.failed_attempts, 'Bounded recorded failed attempts and exact reasons, descending timestamp/ID; not inferred missed plans.'),
    Tool('get_resident_request_summary', c.Activity, q.request_summary, 'Submission counts, distinct reporting-bin counts, current-registry groups/rankings and eligible-bin denominator; repeated submissions remain separate, not distinct residents. A successful zero count means no resident requests for early emptying in the scope/period, not unavailable data.'),
    Tool('list_resident_requests', c.History, q.request_events, 'Bounded raw submission events for selected bin, descending timestamp/ID. Naive local wall-clock times; not verified fill.'),
    Tool('get_resident_request_trend', c.RequestTrend, partial(q.trend, requests=True), 'Submission-count day/week/month buckets, reporting bins, no unique-resident claim; maximum 366 calendar buckets.'),
    Tool('get_requests_since_last_successful_service', c.BinId, q.requests_since_success, 'Latest successful recorded attempt baseline (never replace with later failure), subsequent submissions and separate total; unknown baseline produces NULL subsequent count.'),
    Tool('get_bin_activity_ranking', c.Ranking, q.activity_ranking, 'High-submission/low-success or high-failure rankings with independent attempt/request counts, sample sizes and missing-period-history flags; no causal/overdue inference.'),
    Tool('get_site_activity_summary', c.SiteActivity, q.site_activity, 'Selected member-bin service/submission totals per site. Preaggregates datasets independently, preserving three attempts plus four submissions as three/four.'),
    Tool('get_geographic_context', c.Geography, s.geographic_context, 'Exact district/service-zone intersections, selected-bin membership, unmatched/ambiguous coverage; holes respected, covers includes boundaries, lowest stored ID wins overlaps.', 'source geometry/current registry'),
    Tool('get_geographic_summary', c.GeographicSummary, s.geographic_summary, 'Same-period whole-geography and selected-intersection bin/activity summaries with deterministic lowest-ID spatial membership.', 'source geometry/recorded activity'),
    Tool('get_population_bin_summary', c.Population, s.population_summary, 'Selected current bin coordinates intersect covering source polygons. Unique full-polygon totals counted once, missing/suppressed density and ambiguous/unmatched coverage. Stored allocations per waste stream; never unique residents or clipped bbox population.', 'population estimates'),
    Tool('list_bin_population_context', c.Page, s.population_list, 'Current spatial population context and separately stored source-cell/allocation per selected bin. Holes/boundaries respected, stale allocation possible; missing density unavailable.', 'population estimates'),
    Tool('get_schedule_summary', c.Schedule, q.schedule_summary, 'Stored planned dates/bin coverage and ranges, with explicit future periods allowed. No inference of completed/missed service or complete plan coverage.', 'stored plans', True),
    Tool('list_scheduled_collections', c.Schedule, q.schedule_list, 'Bounded stored planned collection dates, deterministic date/ID order; explicit future dates allowed, distinct from attempts.', 'stored plans', True),
    Tool('get_synthetic_day_summary', c.Synthetic, q.synthetic_summary, 'Stored bin_days status/row/distinct-bin counts; denominator synthetic rows, copied registry and estimated allocation snapshots, not recorded service quality.', 'synthetic outcomes'),
    Tool('get_synthetic_day_trend', c.SyntheticTrend, partial(q.trend, synthetic=True), 'Day/week/month synthetic outcome counts and distinct bins, maximum 366 buckets; rates/statuses stay separate from observed attempts.', 'synthetic outcomes'),
    Tool('get_plan_summary', c.PlanSummary, q.plan_summary, 'Selected stored entries with model-predicted 0–4 distribution and current capacity. Whole represented stops counted once; snapshots include outside bins and are separate from selected subtotals.', 'stored model predictions (synthetic history)', True),
    Tool('list_plan_entries', c.Events, q.plan_list, 'Selected stored stop-bin entries, model-predicted 0–4 level/due and labelled whole-stop planning snapshots; explicit future periods, no generation.', 'stored model predictions (synthetic history)', True),
    Tool('get_landfill', c.FacilityId, q.facility_detail, 'Recorded facility ID detail, nullable coordinates, coordinate quality and source verification; may be outside bbox contextual scope.'),
    Tool('list_landfills', c.Page, q.facility_list, 'Valid-coordinate facilities in bbox, deterministic bounded pagination and source coordinate quality.'),
    Tool('get_nearest_landfills', c.Proximity, q.proximity, 'Maximum ten facilities by haversine distance in metres from explicit coordinate pair or bbox centre. Outside-area results allowed; approximate non-road distance with source quality.'),
    Tool('get_fleet_summary', c.Fleet, q.fleet_summary, 'Global stored fleet counts: active/available versus retired and known available volume; optional exact current carrier, no spatial assignment or route claims.'),
    Tool('compare_area_to_global', c.Compare, q.compare_global, 'Same-window area/global registry/service/submission groups and normalized intensity with numerator/bin denominator. Global includes area, not a municipal census/control group.'),
]
REGISTRY = {tool.name: tool for tool in TOOLS}


def strict_schema(model):
    schema = model.model_json_schema()
    def close(node):
        if isinstance(node, dict):
            node.pop('default', None)
            if node.get('type') == 'object':
                node['additionalProperties'] = False
                node['required'] = list(node.get('properties', {}))
            for value in node.values(): close(value)
        elif isinstance(node, list):
            for value in node: close(value)
    close(schema)
    return schema


def definitions():
    return [{'type': 'function', 'name': tool.name, 'description': tool.description, 'parameters': strict_schema(tool.inputs), 'strict': True} for tool in TOOLS]


def catalogue():
    return {'common_semantics': {
        'scope': 'Trusted bbox is automatic. NULL scope means area; explicit global includes area and all eligible stored bins. Detail IDs are internal and area-validated; facilities/fleet are contextual.',
        'time': 'NULL period means last 30 Europe/Vilnius dates including partial today, capped at captured run start for observations. Explicit start/end dates use exclusive end. all_history has no lower bound. Future only schedules/stored plans.',
        'pagination': 'NULL limit/offset means 50/0; maximum 100 records/IDs, 366 trend buckets; deterministic next_offset and has_more. Output-size trimming is explicit.',
        'NULL': 'Unknown/missing/unavailable stays NULL; numeric special capacity values excluded; zero counts do not establish full source coverage. Failed reads have status error.',
        'units': 'Capacity uses unverified source m³ assumption; observed fill ordinal 0–3, model-predicted fill 0–4 (from synthetic history); population estimates and per-stream allocations are not unique residents.',
        'result': c.Result.model_json_schema(),
    }, 'tools': [{'name': tool.name, 'description': tool.description, 'evidence_type': tool.evidence, 'input': strict_schema(tool.inputs), 'result_type': tool.result_type.__name__} for tool in TOOLS]}


def normalized(value):
    if isinstance(value, (date, datetime)): return value.isoformat()
    if isinstance(value, Decimal): return float(value) if value.is_finite() else None
    if isinstance(value, float): return value if isfinite(value) else None
    if isinstance(value, dict): return {str(k): normalized(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)): return [normalized(v) for v in value]
    return value


def error_result(ctx, code, message):
    return c.Result(status='error', code=code, message=message, scope='area', evidence_type='failed/rejected read', queried_at=ctx.started_at.isoformat())


def serialize(result, ctx, budget=True):
    body = result.model_dump(mode='json')
    cap = min(16384, max(1024, 49152 - ctx.result_bytes)) if budget else 16384
    def encoded(): return json.dumps(body, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    omitted = {}
    def arrays(value, path='data'):
        found = []
        if isinstance(value, dict):
            for key, item in value.items(): found.extend(arrays(item, path + '.' + key))
        elif isinstance(value, list):
            if value: found.append((path, value))
            for index, item in enumerate(value): found.extend(arrays(item, path + '.' + str(index)))
        return found
    while len(encoded().encode()) > cap:
        available = arrays(body['data'])
        if not available:
            body = error_result(ctx, 'result_size', 'Scalar result exceeds remaining payload budget; narrow query.').model_dump(mode='json')
            break
        path, array = max(available, key=lambda entry: len(json.dumps(entry[1], ensure_ascii=False)))
        array.pop()
        omitted[path] = omitted.get(path, 0) + 1
        body['data']['output_truncation'] = {'omitted_by_path': omitted, 'complete': False}
    # Pagination after size trimming must start at the first omitted record/group.
    for key in ('records', 'groups', 'buckets'):
        if 'data.' + key in omitted:
            data = body['data']
            data['returned_count'] = len(data[key])
            data['has_more'] = True
            if key != 'buckets': data['next_offset'] = data.get('offset', 0) + len(data[key])
    output = json.dumps(body, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    if len(output.encode()) > cap and body['status'] == 'ok':
        output = error_result(ctx, 'result_size', 'Result exceeds payload cap; narrow query.').model_dump_json()
    if budget: ctx.result_bytes += len(output.encode())
    return output


def dispatch(factory, ctx, name, arguments, exploration=True):
    started = monotonic()
    tool = REGISTRY.get(name)
    if not tool: return error_result(ctx, 'unknown_tool', 'Tool is not registered.')
    try:
        args = tool.inputs.model_validate_json(arguments)
        period = ctx.period(getattr(args, 'period', None), future=tool.future)
        if ctx.remaining(exploration) <= 0: return error_result(ctx, 'deadline', 'Analytical phase expired.')
        if ctx.tool_calls >= 12: return error_result(ctx, 'tool_budget', 'Twelve executed tools per run maximum.')
        ctx.tool_calls += 1
        with analytical_session(factory, ctx, exploration) as session:
            data = normalized(tool.query(session, ctx, args))
            read_only = session.scalar(text('SHOW transaction_read_only')) == 'on'
            if not read_only: raise RuntimeError('Read-only invariant failed')
        scope = 'global_fleet_context' if name == 'get_fleet_summary' else 'facility_context' if name in ('get_landfill', 'get_nearest_landfills') else 'area_and_global' if name == 'compare_area_to_global' else 'area_and_geography' if name == 'get_geographic_summary' else 'area_site_locations' if name == 'list_sites' else getattr(args, 'scope', None) or 'area'
        result = tool.result_type(status='ok', scope=scope, period=period, evidence_type=tool.evidence, queried_at=datetime.now(ctx.started_at.tzinfo).isoformat(), data=data)
    except c.ToolQueryError as error:
        result = error_result(ctx, error.code, str(error))
    except (ValidationError, ValueError, json.JSONDecodeError):
        result = error_result(ctx, 'invalid_arguments', 'Invalid tool arguments or unsupported data; check catalogue and bounds.')
    except TimeoutError:
        result = error_result(ctx, 'deadline', 'Analytical phase expired.')
    except SQLAlchemyError:
        result = error_result(ctx, 'deadline', 'Analytical phase expired.') if ctx.remaining(exploration) <= 0 else error_result(ctx, 'query_failed', 'Stored data read failed; this is not empty evidence.')
    logger.info('analytics tool run=%s name=%s status=%s duration=%.3f calls=%s', ctx.correlation_id, name, result.status, monotonic() - started, ctx.tool_calls)
    return result
