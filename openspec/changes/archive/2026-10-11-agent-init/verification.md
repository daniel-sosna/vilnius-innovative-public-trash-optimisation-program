# Verification

## Development data preflight (task 3.1)

Docker access works within `newgrp docker` subshells. Started the existing stack
with `docker compose up -d`; default frontend/backend ports are 5173/8000.

The configured host directory is `backend/data`, mounted at `/app/data`.
Required exports are present: `sites_202610092000.csv`,
`bins_202610091935.csv`, `bin_hist_202610091935.csv`.
`population_density_1ha.geojson` is also present. No import, VASA fetch,
population rebuild or optional-data rebuild was performed.

Verified exact stored counts in a read-only transaction using:

```bash
newgrp docker <<'EOF'
docker compose exec -T backend uv run python - <<'PY'
from sqlalchemy import create_engine, select, func, text
from app.core.config import Settings, data_dir
from app.infrastructure.models import Base
import re
p = data_dir()
print('data_dir:', p)
for name in ('sites', 'bins', 'bin_hist'):
    files = [f.name for f in p.glob(name + '_*.csv')
             if re.fullmatch(name + r'_\d+\.csv', f.name)]
    print(name, 'exports:', ','.join(files))
    if not files:
        raise SystemExit(1)
engine = create_engine(Settings().database_url)
with engine.connect() as c:
    c.execute(text('SET TRANSACTION READ ONLY'))
    for name in ('sites', 'bins', 'bin_hist', 'resident_requests',
                 'bin_schedule', 'population_cells', 'bin_population',
                 'bin_days', 'collection_stops', 'stop_bins',
                 'district_boundaries', 'service_zones', 'landfills', 'trucks'):
        table = Base.metadata.tables[name]
        count = c.scalar(select(func.count()).select_from(table))
        column = next((table.c[k] for k in ('date', 'timestamp', 'collection_date')
                       if k in table.c), None)
        span = c.execute(select(func.min(column), func.max(column))).one() \
            if column is not None else None
        print(name, 'rows:', count, 'date range:', span)
    c.rollback()
PY
EOF
```

| Dataset | Rows | Available stored dates |
|---|---:|---|
| sites | 9,464 | — |
| bins | 21,951 | — |
| bin_hist | 201,045 | 2026-09-09 05:04:52 to 2026-10-09 13:18:20 |
| resident_requests | 0 | available; no recorded requests |
| bin_schedule | 203,222 | 2026-10-01 to 2026-10-31 |
| population_cells | 14,079 | — |
| bin_population | 21,951 | — |
| bin_days | 0 | unavailable |
| collection_stops | 5,730 | 2026-10-10 |
| stop_bins | 16,139 | — |
| district_boundaries | 21 | — |
| service_zones | 5 | — |
| landfills | 3 | — |
| trucks | 0 | — |

UI verification was completed and accepted by the user.

## Implementation and local checks

The user confirmed that they personally checked everything and all results
were satisfactory, and authorized completion of the remaining tasks and spec
sync. Manual UI and live-provider verification are recorded as user-reported
acceptance; the agent's independently performed checks are listed separately.

- All 35 catalogue entries have callables, strict closed input schemas and
  registry-generated documentation. Every entry returned `ok` in a dense-area
  local invocation with limit 3; largest serialized result was 8,644 bytes.
- Dense bbox `54.68 25.27 54.70 25.30`: 1,515 bins, 498 represented sites,
  491 location sites; recent service 21,504 attempts, 20,710 successes and 794
  failures. Imported fill is all NULL and its ordinal mean remains NULL.
- Empty bbox `0 0 0.1 0.1`: zero counts, NULL capacity sum/mean and NULL success
  rate. Required source coverage and optional absence are reported separately.
- Invalid tools, extra SQL fields, unsupported grouping, negative IDs and limit
  101 are rejected without executing a query.
- A 100-row bin listing was reduced to 24 records at 16,116 bytes, with explicit
  omitted count and `next_offset=24` rather than implying a complete result.
- Current population context reports candidate polygon 14079 as invalid and
  unavailable, without repair. In the dense bbox, 265 distinct valid source
  polygons contribute 18,372 full-polygon estimated residents once, with 40
  selected bins missing density. Per-stream stored allocations remain separate.
- A future schedule window `[2026-10-12, 2026-11-01)` returns 15,168 planned
  dates for 1,473 bins, without treating them as observations.
- A two-year daily request trend returns `bucket_limit`, including when no
  submissions exist. Weekly/monthly and all-history queries succeed.
- Captured default windows across both Europe/Vilnius DST changes cover 30
  local calendar dates, without assigning UTC to naive source timestamps.

Repeatable local commands (prefix Docker commands with `newgrp docker` when
this shell needs refreshed group membership):

```bash
docker compose exec -T backend uv sync --locked
docker compose exec -T backend uv run python -m app.interfaces.analytics_agent.check --catalogue
docker compose exec -T backend uv run python -m app.interfaces.analytics_agent.check --guide
docker compose exec -T backend uv run python -m app.interfaces.analytics_agent.check --bbox 54.68 25.27 54.70 25.30 --full
docker compose exec -T backend uv run python -m app.interfaces.analytics_agent.check --bbox 0 0 0.1 0.1 --full
docker compose exec -T backend uv run python -m app.interfaces.analytics_agent.check --bbox 54.68 25.27 54.70 25.30 --tool get_population_bin_summary --arguments '{"grouping":"waste_type","limit":3}'
docker compose exec -T backend uv run python -m app.interfaces.analytics_agent.check --bbox 54.68 25.27 54.70 25.30 --tool get_schedule_summary --arguments '{"period":{"mode":"explicit","start":"2026-10-12","end":"2026-11-01"}}'
docker compose exec -T backend uv run python -m app.interfaces.analytics_agent.check --bbox 54.68 25.27 54.70 25.30 --tool get_service_trend --arguments '{"metric":"fill","interval":"week","period":{"mode":"all_history","start":null,"end":null}}'
docker compose exec -T backend uv run python -m app.interfaces.analytics_agent.check --bbox 54.68 25.27 54.70 25.30 --tool list_bins --arguments '{"limit":100}' --full
docker compose exec -T backend uv run python -m app.interfaces.analytics_agent.check --bbox 54.68 25.27 54.70 25.30 --live
```

## Analytical edge cases

Manual local invocations used connection-local temporary copies of table
structures, then queried them through the actual registry and rollback-only
snapshots. No original application table was written or rebuilt; disposing the
connection discarded the temporary data. No automated test suite was added.

| Scenario | Observed result |
|---|---|
| Three attempts plus four submissions for one bin | Ranking preserves 3 attempts / 4 submissions |
| Two repeated submissions at the same timestamp | Both remain counted |
| Two successes and one later failed attempt | Success rate 2/3; latest attempt differs from latest success |
| Fill values 0, 2, NULL | Observed 2, missing 1, mean 1; all four categories retained |
| No successful baseline, one submission | Since-service count NULL; total submission count 1 |
| Site owns three bins, two selected, site location outside | Whole-site 3 versus selected 2; location site excluded |
| All source capacities NULL | Known count 0; sum/mean NULL |
| NULL current carrier with attempts | NULL carrier group retained |
| Bin in polygon hole | Unmatched; no envelope-only membership |
| Bbox wholly within polygon hole | Envelope overlaps, exact intersection false |
| Bin on shared boundary | Lowest polygon ID assigned once, ambiguity count 1 |
| Two selected bins cover one 100-resident polygon | Full-polygon context stays 100, not 200 |
| Stored allocations in two waste streams | Separate stream totals; no unique-resident combined sum |
| One selected mock entry, outside member at same stop | Mock category 4 retained; whole-stop 100/60 snapshots separate |
| Three trucks: available, unavailable, retired | Active 2, available 1, retired 1; available volume 10 |
| NULL-coordinate facility and outside valid facility | NULL excluded from proximity; valid outside context returned |
| Same-period area/global comparison | Area denominator 3, global 4; global explicitly includes area |
| Dec 31 / Jan 1 service dates | Same ISO week starts Dec 28; month buckets keep separate full years |

## Execution and API checks

Manual local provider traces used the real run loop with deterministic local
responses; no outbound model requests were made in these traces.

| Trace | Outcome |
|---|---|
| Overview followed by final answer | Complete at request 2 |
| Six calls in each investigation response | Four executed per response; all six call IDs receive matching outputs |
| Continued investigation | Request 5 uses synthesis mode; no request 6 |
| Empty final | Incomplete `no_final_answer` |
| Truncated final | Incomplete `model_response_incomplete`, partial text retained |
| Refusal | Incomplete `refused` |
| Provider exception | Controlled failure, one counted request |
| Context already expired | Incomplete `deadline`, zero provider calls |

A `SELECT pg_sleep(3)` invocation with 0.2 seconds left in the exploration
phase stopped in approximately 0.21 seconds; `transaction_read_only` was `on`
and the pool had zero checked-out connections afterwards.

HTTP requests confirmed valid input without credentials returns 503, while
zero/reversed/NaN bounds and extra body/bbox fields return 422. All five map GET
endpoints return 200 with their existing FeatureCollection structure. An
in-process ASGI request with a local failing provider adapter returned 502 and
safe `provider_failed` feedback without contacting OpenAI.

Official documentation consulted through the Developer Docs MCP:
[function calling](https://developers.openai.com/api/docs/guides/function-calling),
[reasoning continuation](https://developers.openai.com/api/docs/guides/reasoning),
[Python SDK](https://developers.openai.com/api/docs/libraries),
[errors](https://developers.openai.com/api/docs/guides/error-codes).

## Build and packaging checks

- Native and container frontend builds and lint pass. Vite reports the existing
  large-bundle warning; no build failure.
- Backend `uv sync --locked` and module import/compile checks pass.
- Default and worktree Compose configuration checks pass with `config --quiet`.
- Native and development-container assembled guides compare identically.
- Built-image guide resolves from `/app/agent-domain`. Image checks find no
  `/app/.env`, `/app/data`, `/app/node_modules` or `/app/frontend`.
- Runtime guide includes canonical semantic text and excludes sample export
  counts, illustrative rows and site-detail UI presentation rules.
- `git diff --check` and `openspec validate agent-init --strict` pass.
- Final backend image rebuilt and running with `newgrp docker` followed by
  `docker compose build backend` and `docker compose up -d backend`.
  Native, development-container and built-image guides share SHA-256
  `24cca286b9710d435767b7be6bf384dec0fd9b44bd26732e485ceac5b35d739c`.
  All three documentation mounts are read-only. The running frontend route
  and backend OpenAPI endpoint return 200; analysis without configuration
  returns the controlled 503 `analysis_configuration` response.

## User validation checklist (accepted by user)

At http://localhost:5173/admin/map-analytics, check desktop and 320px widths:

1. The map fills the remaining space below collapsed/expanded navigation.
   Sites and trucks keep their existing page layouts.
2. Layers and AI switch one panel; close and Escape restore trigger focus.
   Zoom controls and attribution remain reachable.
3. All five layers, filters, legends, loading/error/retry feedback, clustering
   and popups remain usable; switching panels preserves camera and loaded data.
4. Draw an area with mouse and touch over active layers, in both directions.
   Drawing/review prevents panning and feature activation; cancellation restores
   interaction. Confirm, retake and cancel behave as labelled.
5. Check rotated/pitched selections, invalid/zero-area gestures, geographic
   review and retained noninteractive selection while navigating.
6. Configure the backend AI key/model using docs/development.md, recreate the
   backend and run explicit `--live` before checking formatted answers.
7. During analysis, navigate and switch panels; duplicate submissions and area
   replacement stay disabled. Hidden layers/categories remain analytically
   eligible. Retry incomplete/error results; navigate away during a run and
   confirm late responses do not reappear after returning.
8. Validate model compatibility, observed/estimated/synthetic labels, real
   provider failure and deadline recovery. The user confirmed satisfactory results for all checks.

## User feedback implementation checks

- AI/layer controls have opaque light/dark backgrounds, including hover states.
- The separate `Laikotarpis` timestamp line is removed from the result panel.
- Responses render Markdown with GFM tables and raw HTML disabled. Table overflow
  scrolls within the panel; headings, lists, quotations and code have formatting.
- Completed answers hide the analysis action. Errors and incomplete results
  expose `Bandyti dar kartą`; confirming a new area exposes the analyze action.
- The run and response contract permit five model rounds, with synthesis on the
  fifth and automatic SDK retries disabled. The 60-second deadline remains.
- Actual round/tool/synthesis events stream to the pending panel. Private model
  reasoning is excluded. JSON clients retain the existing response contract.
- Manual local provider trace reached five rounds, synthesized on the fifth,
  emitted actual stage callbacks and closed the provider. In-process ASGI
  checks with `uv run --with httpx python` confirmed ordered progress/result
  frames, JSON compatibility and safe stream errors; no outbound model call.
- `newgrp docker` with `docker compose exec -T frontend npm run build` and
  `npm run lint` passes. Native build encountered container-owned `dist`
  permissions; the container build succeeds. Visual review was accepted by the user.

## Resident zero-count and loading refinements

- Real selected-area overview returns resident coverage `rows: 0`, `bins: 0`,
  `available: true`; recent summary returns `submissions: 0`, `reporting_bins: 0`
  for 1,515 eligible bins. Zero means no recorded early-emptying requests.
- Both maintained analytical guidance and the runtime data dictionary specify
  zero-request semantics; the tool description reinforces them.
- Pending text pulses between full and 40% opacity every 1.6 seconds. Reduced
  motion disables the animation. Each investigation round uses a different
  phrase, final synthesis has its own phrase, and no round counter is displayed.
- A local provider trace verifies five total requests, tool-free synthesis on
  the fifth, per-round progress events and provider cleanup.
- Container frontend build/lint, `git diff --check` and strict OpenSpec validation
  pass. Visual animation and live generated wording were accepted by the user.

## Selected-layer legend refinement

Legend receives the selected layer definitions only. Unselected layer swatches
are hidden; with no selected layer it displays `Nepasirinktas sluoksnis`.
District/zone layers retain their existing lack of legend entries.

## Final acceptance

The user stated: “I have checked everything myself and evrything ok you can complete the tasks and also sync”. All remaining verification tasks are accepted on that basis. All 33 tasks are marked complete.

## Spec sync and archive checks

All four delta specs are synced into main specs. Existing main-spec titles, purposes and unrelated requirements are preserved. All delta requirements and scenarios match their main-spec counterparts. Main-spec validation passed for all 19 specs; strict change validation and `git diff --check` passed. Documentation links point to main specs.
