# Design

## Context

See [proposal.md](proposal.md) for motivation and scope. The contracts are in the four [spec deltas](specs/).

`MapAnalyticsPage` owns independent layer loading and bin filters. `AnalyticsCanvas` constructs MapLibre in an effect depending on the stable layer definitions, basemap style and explicit retry revision; selection/data changes use its existing runtime. A `ResizeObserver` already resizes the canvas. The admin layout imposes a content-width maximum and padding, and the map has fixed/minimum height styles. The layer list and legend share a below-map card, while waste categories use a modal.

FastAPI exposes map reads through `app/interfaces/map_analytics`. `collection_session` enforces short repeatable-read, read-only transactions with statement/lock timeouts and rollback. SQLAlchemy sessions are synchronous. Geometry is stored as JSONB and point coordinates, without PostGIS. The allocation CLI has polygon/hole logic, but its stored mappings can lag registry edits and do not provide general polygon intersection.

The current models expose 14 analytically useful tables: sites, bins, bin_hist, resident_requests, bin_schedule, population_cells, bin_population, bin_days, collection_stops, stop_bins, district_boundaries, service_zones, landfills and trucks. Import bookkeeping is excluded. No route, historical truck attribution, service duration or persisted model-training result exists. Domain meanings are documented in `docs/data-model.md` and `docs/data/bin-days-columns.md`.

## Goals / Non-Goals

**Goals:** Keep one map runtime and one FastAPI deployment; make analytical queries reusable independently of OpenAI; enforce execution budgets in the backend; expose evidence provenance and coverage; deliver a real selection-to-answer vertical slice before broadening the catalogue.

**Non-Goals:** Change stored schema, imports, population allocation, simulation or prediction generation. UI state is page-session state; no jobs service, conversation store, persistent run table or streaming protocol is introduced. Full exclusions remain in the proposal.

## Decisions

### 1. Map route fills the remaining layout space

Give the analytics route a viewport-height flex layout: the existing admin header occupies natural height and the map region takes the remaining space with `min-height: 0`. Remove that route's content maximum, page padding, visible heading and map border/card sizing. Preserve an accessible page name. Other admin routes retain their existing content layout. Avoid subtracting a hard-coded navbar height because mobile navigation wraps and expands.

Keep `AnalyticsMap` mounted at one stable position regardless of panel state. Leave `useLayerSession`, `useBinFilters` and stable `mapLayers` ownership in the page. Extend map props with a small selection interface; synchronize callbacks and overlays outside the map-construction effect. Explicit basemap retry remains the only recovery-driven reconstruction path.

### 2. One responsive, nonmodal map panel

Use one `sidebarMode: null | layers | ai` and one shared panel shell. A floating button opens its mode, switches from the other mode, or closes its already-active mode. Use a right-hand desktop panel of approximately 360px; on phones use a bounded bottom panel that leaves a map portion and floating controls reachable. Both have internal scrolling, a labelled close action, Escape dismissal and focus restoration. Avoid the current modal Dialog's full-screen backdrop/focus trap: the map must remain usable while the panel is open. This does not require a new drawer dependency.

Render dataset controls as a vertical list, waste categories indented under bins, then the legend entries of selected layers as a vertical list, displaying `Nepasirinktas sluoksnis` when no layer is selected. Retain default unchecked datasets, category defaults, independent retry/empty/loading states and cache semantics. UI presentation changes do not modify point or polygon renderers.

Keep `confirmedBbox`, draft selection, pending run and answer above the switchable contents. Closing the panel never aborts the run. Confirming a replacement clears the prior area result. Navigating away from the page aborts the client request and ignores late results; backend work remains bounded even if client disconnection cannot immediately stop the provider.

### 3. Draft selection is separate from confirmed geography

Use a pointer-capture overlay during selection so dragging cannot activate renderer handlers or pan/zoom the canvas. Record and restore each previously enabled navigation handler rather than enabling everything on exit. Temporarily close the shared panel during drawing/review and return to AI on confirmation or cancellation. Support pointer cancellation and Escape, and remove all listeners/capture on exit or disposal.

Draw the screenshot-style draft rectangle in screen coordinates. Convert all four corners with the current map's unprojection, normalize the longitude/latitude envelope and reject nonfinite, zero-area or geographically invalid results. During review, render the actual bbox as a geographic polygon, making any difference on rotated/pitched maps visible before confirmation. Do not reset bearing/pitch or move the camera. A confirmed, non-interactive GeoJSON outline/fill follows normal map projection and stays visible during navigation without intercepting marker or population clicks.

This is a local Vilnius workflow: antimeridian-crossing selection and unprojectable sky areas are rejected with retake feedback rather than silently interpreted as a different area. Analysis replacement and submission are disabled during the pending run; navigation and panel/layer controls remain enabled.

### 4. Thin endpoint, reusable queries, explicit registry

Extend the map router and schemas with `POST /map-analytics/agent/analyze`. Put orchestration, instructions, tool input/result contracts, registry and query modules in `app/services/analytics_agent/`; put the provider adapter in `app/integrations/openai.py`. A flat registry connects stable function names, Pydantic input types, descriptions, result types and callables. Query functions receive a trusted run context and a read-only session, never model-supplied SQL. Registry dispatch and result formatting stay independent of the provider.

The trusted context contains the bbox, captured local run-start time, default period, monotonic deadline and correlation ID. Area tools use that bbox automatically; the model cannot replace it. Explicit global/geographic comparison tools permit broader summaries and identify the baseline. Detail/ID tools validate selected-area membership; the facility proximity tool deliberately permits outside-area contextual results. `get_site` distinguishes selected member summaries from whole-site registry detail.

Generate Responses `type: function` definitions from input types and registry metadata, explicitly setting `strict: true`. All object schemas are closed and properties are required; nullable values represent optional choices with server-applied defaults. Validate again locally, including argument combinations, supported enums, bounded IDs and periods. Handle every returned call ID, including invalid or over-budget calls, with a structured output rather than dropping calls. This follows the [official function-calling schema and execution guidance](https://developers.openai.com/api/docs/guides/function-calling).

### 5. Catalogue covers analytical angles without duplicate functions

Common input concepts are bounded `limit`/`offset`, a period selector (`recent`, explicit dates, or `all_history`), fixed grouping enums and an explicit summary scope. These are predetermined query choices, not a database query language. Defaults are 50 raw rows, maximum 100 rows/IDs, at most 366 trend buckets, four executed tool calls per investigation response and twelve per run. Extra requested calls receive a budget result linked to their call ID. Bound serialized outputs to 16 KiB per tool and 64 KiB over the run; paginate record/group arrays before serialization and report effective counts, next offset and any omitted groups. If even a scalar result exceeds the cap, return an explicit result-size error.

| Tool | Inputs beyond trusted area context | Structured evidence |
|---|---|---|
| `get_area_overview` | none | Registry counts, represented/location-site counts, capacity coverage, recent activity, available date ranges and optional-dataset coverage |
| `get_bin` | bin ID | Registry detail, site reference and evidence availability |
| `get_bins_by_ids` | bounded bin IDs | Selected-area records and missing/outside IDs |
| `list_bins` | waste type/carrier/group filters, investigative sort, cutoff, pagination | Bin rows, latest successful attempt and unknown-history status where requested |
| `get_bin_summary` | area/global scope, grouping | Count, total/average known capacity and coverage; groups include NULL/source values |
| `get_site` | site ID | Site identity, coordinates and whole-site versus selected-member counts |
| `list_sites` | pagination | Sites whose own stored locations lie inside the bbox |
| `get_site_summary` | optional site ID, waste/carrier grouping or count/capacity rank, pagination | Selected-member site totals, breakdowns and rankings |
| `get_bin_service_history` | bin ID, period, pagination | Raw attempts ordered by timestamp/ID |
| `get_service_summary` | area/global scope, optional bin ID, grouping, period | Attempts, successes, failures, rates, latest attempt/success and history coverage |
| `get_service_failure_reasons` | area/global scope, grouping, period, pagination | Failure-reason frequencies, including NULL/empty reasons |
| `get_fill_summary` | area/global scope, grouping, period | Recorded 0–3 category counts, ordinal mean and observed/missing coverage |
| `get_service_trend` | service/failure/fill metric, scope, period, day/week/month | Bounded buckets with counts and valid denominators |
| `list_failed_service_attempts` | period, pagination | Recorded failed attempts and reasons |
| `get_resident_request_summary` | scope, optional bin ID, grouping, period, pagination | Submission counts, distinct reporting-bin counts and rankings |
| `list_resident_requests` | bin ID, period, pagination | Bounded submission events |
| `get_resident_request_trend` | scope, period, day/week/month | Submission-count buckets |
| `get_requests_since_last_successful_service` | bin ID | Successful baseline timestamp or unknown baseline, subsequent request count |
| `get_bin_activity_ranking` | high-requests/low-successes or high-failures rank, period, pagination | Component counts, sample sizes, latest success and missing-history flags |
| `get_site_activity_summary` | optional site ID, period, pagination | Selected-bin service/request activity aggregated independently |
| `get_geographic_context` | district/service-zone kind, pagination | Actual intersecting polygon IDs/names and membership coverage |
| `get_geographic_summary` | kind, geographic ID, period | Whole-geography and selected-intersection bin/activity summaries |
| `get_population_bin_summary` | polygon/density-band/waste-type grouping, pagination | Selected-bin membership, unique source polygons, uncertainty and per-stream allocation totals |
| `list_bin_population_context` | pagination | Spatial polygon context and separately stored allocation for each selected bin |
| `get_schedule_summary` | scope, optional bin ID, period | Planned-date and bin coverage; explicit future periods allowed |
| `list_scheduled_collections` | optional bin ID, period, pagination | Stored planned dates, without inferred completed events |
| `get_synthetic_day_summary` | grouping, period | Synthetic status counts, row/distinct-bin coverage and estimated/copied field meanings |
| `get_synthetic_day_trend` | period, day/week/month | Synthetic outcome buckets, separately labelled |
| `get_mock_plan_summary` | period, carrier grouping | Mock predicted-fill distribution, selected entries and labelled whole-stop snapshot totals |
| `list_mock_plan_entries` | period, pagination | Selected stop-bin entries with mock 0–4 predictions and due flags |
| `get_landfill` | facility ID | Recorded facility context, coordinate quality and source verification fields |
| `list_landfills` | pagination | Facilities inside bbox with valid coordinates |
| `get_nearest_landfills` | bbox-center or explicit coordinate reference, maximum 10 | Haversine distance in metres to reference, quality and explicit non-road basis |
| `get_fleet_summary` | optional current carrier | Global active/available truck count and known volume, explicitly outside geographic bin scope |
| `compare_area_to_global` | grouping, period | Same-period area/global counts and normalized activity, with denominators and global inclusion rules |

Carrier performance and waste-type comparison reuse grouped service/request tools. Largest-capacity and service-gap bins reuse the investigative listing. Global waste/carrier summaries reuse explicit global scope rather than additional synonymous functions. Every entry is required; a callable is registered only once its implementation and documentation exist, and the completed change must expose the full catalogue.

### 6. Spatial precision without database GIS infrastructure

Use indexed scalar bbox predicates for point discovery and stored population-envelope fields to narrow candidate polygons in PostgreSQL. Use Shapely for exact polygon/bbox intersection and boundary-inclusive point membership, handling holes and choosing the lowest ID when multiple polygons cover a point. Report ambiguous, unmatched and missing-density counts. Invalid stored polygons are unavailable and excluded without repair; report their candidate IDs and explain that unmatched means no valid covering geometry, with membership potentially concealed by excluded invalid candidates. An explicitly requested invalid geography returns unavailable evidence instead of inferred totals. Prepare/cache candidate geometry only within the run; do not preload every dataset before analysis or add cross-run caches that conceal edits.

The allocation CLI's ray-casting helper remains untouched. Reusing it directly would not solve polygon/bbox intersection or fully specify shared-boundary behavior. Shapely is one backend library rather than a GIS service or PostGIS schema change; its [covers](https://shapely.readthedocs.io/en/stable/reference/shapely.covers.html) and [intersects](https://shapely.readthedocs.io/en/stable/reference/shapely.intersects.html) predicates support the selected behavior. No polygon clipping/population estimation inside the rectangle is introduced.

Join current selected-bin coordinates to population polygons rather than treating potentially stale `bin_population.population_cell_id` as authoritative geography. Expose stored `resident_factor` separately, retaining its nearest-collection-point/per-waste-stream allocation meaning. Polygon totals are counted once as full-polygon context and are never labelled bbox population or unique bin customers. Landfill proximity uses a bbox-center reference unless an explicit coordinate is supplied; it is not distance to the rectangle boundary.

### 7. Time, statistics and provenance are part of results

Capture Europe/Vilnius `run_started_at` once. The recent window starts at midnight 29 calendar dates before today and ends at run start for timestamped records; calendar-date windows are half-open through tomorrow's local date, labelled partial today. `all_history` has no lower observation bound and ends at run start. Explicit future windows are supported only for schedules and stored mock plans. Group weeks by ISO week start, not week number alone. Do not assign UTC to naive stored history/request timestamps or invent a source timezone conversion; their local wall-clock semantics remain documented.

Use database-side filters/aggregation and distinct identities. Preaggregate history and requests independently by bin before combining them; summarize stop-bin entries before joining whole-stop metadata. Capacity statistics include finite known source values, report missing/invalid counts and preserve the unverified unit assumption. Rates return numerator, denominator and null for denominator zero. Recorded fill uses its 0–3 scale with an explicitly ordinal mean. Mock predictions retain 0–4; simulation uses its own outcome statuses.

Each result includes scope, effective period, evidence type, relevant coverage, units/assumptions and limitations. A compact `data` payload contains the requested figures or records. Errors have stable codes and safe messages. Zero rows, unknown values, missing optional coverage and failed reads have distinct representations. Global includes all eligible stored bins including the selected area, not an assumed municipal census or area-excluding control group. Historical spatial/carrier summaries use current bin registry attribution and cannot establish historical location or who performed service.

### 8. Responses orchestration has one hard budget

Use the official SDK's asynchronous client behind the provider adapter, with automatic retries disabled. Count every outbound model request before dispatch; failures also consume a request. Keep accumulated input/output items in memory for that run, including reasoning items required by the configured model, and return JSON tool outputs by `call_id`. Prefer stateless continuation with `store=false`, using encrypted reasoning content where required by current Responses documentation. Repeat the same instructions and available definitions on each investigation request. Do not persist or reuse context across runs.

Force the first request to call `get_area_overview`; no analytical data is fetched before this call. Requests two through four can investigate multiple dimensions or older periods. A complete early final answer ends the run. Request five includes all accumulated evidence, removes function tools and requests synthesis. Refusal, truncation, empty final output or further calls in synthesis cannot be classified as a complete answer. Internal reasoning text is never displayed or logged.

Start a monotonic deadline at validated run creation. Reserve the final 15 seconds for synthesis and stop investigation by 45 seconds, synthesizing earlier if needed with the next remaining request. Individual investigation provider calls have a maximum 12-second timeout capped by the remaining exploration budget; synthesis uses remaining time capped at the run deadline. This reserve is an implementation default inside the confirmed 60-second/five-request ceilings. A provider failure returns a controlled failure; it does not trigger an uncounted retry.

Run synchronous query batches off the async event loop, sequentially within each batch and with session ownership confined to that worker. Open short read-only transactions using the collection-read pattern and close them before the next provider call. Set statement/lock deadlines to the smaller of the existing caps and remaining phase time, check the deadline before every query, and request cancellation of active database work on phase/run expiry. Provider and database work must be deadline-bounded; merely timing out the HTTP handler while work continues unrestricted is insufficient. Produce a matched budget/error output for unexecuted calls when transitioning to synthesis.

Short snapshots avoid holding a connection throughout network waits. They do not guarantee a single database snapshot across the run: record query time and disclose that registry/events may change between calls. A coherent run-wide transaction was rejected because it would occupy a connection during multiple provider requests.

### 9. API results and UI ownership are explicit

The request has only `bbox`; Pydantic forbids extras. The response has `status: complete | incomplete`, `bbox`, `default_period`, nullable `answer`, nullable `incomplete_reason`, `model_requests` and `elapsed_seconds`. Incomplete reasons include `deadline`, `model_response_incomplete`, `no_final_answer` and `refused`. Budget/incomplete outcomes return HTTP 200 with that explicit status. Invalid input returns 422, missing key/model returns 503 and provider failures return 502 with a stable error code and safe message. Database unavailability remains a failed read; recoverable individual tool failures are supplied as error evidence and must limit the final claims.

The AI panel renders formatted text as Markdown with raw HTML disabled using a small renderer dependency, preserves area/result provenance and exposes incomplete or failure feedback in Lithuanian. A null answer shows an incomplete state rather than an empty success. Pending state disables only analyze and area replacement. The client deadline is slightly above 60 seconds to allow response transport; it does not grant backend execution extra time. A lost connection releases pending UI with retry, and retry starts a new run with the same bbox.

### 10. Runtime documentation has maintained sources

Maintain `docs/agent-skills.md` as the dedicated skills/guidance file. It provides the analytical procedure and references the canonical data dictionary and catalogue. Extend `docs/data-model.md` with concise agent-visible primary keys, relationships, important columns, units, NULL meanings and provenance for every exposed table; keep the detailed bin-day dictionary in its existing file. Generate the tool catalogue from registry descriptions/types, including result shapes, so dispatch, provider schemas and documentation cannot drift independently.

The runtime guide loader combines guidance and marked metadata-only sections of the canonical dictionaries with the generated catalogue, not unresolved Markdown links. Mark maintained domain/column semantics for runtime use and exclude illustrative export counts, empirical dataset statistics and sample records from initial context; real quantities must come from tools. Package the required docs into the backend image: change only the backend build context to the repository root with `backend/Dockerfile`, prefix existing COPY sources accordingly, and copy just the named documents to `/app/agent-domain`. Add a root `.dockerignore` excluding secrets, Git metadata, exports, virtual environments and frontend dependencies. Mount the same documents read-only at that path in the development Compose backend so editing documentation does not require a rebuild. Native runs resolve canonical files from the repository root. No runtime documentation MCP or network/file-search tool is introduced.

Keep configuration/run instructions in `docs/development.md` and behavioral contracts in the specs; link them from runtime guidance rather than restating UI/API rules in docs. Update README's existing map feature row and documentation index only. A verification command under `app/interfaces/analytics_agent/check.py` can print the registry catalogue and exercise local queries through rollback-only snapshots; live-model invocation is an explicit separate mode. The command is a repeatable diagnostic, not an automated test suite. Manual scenarios and captured evidence stay under this change.

### 11. Configuration and existing consumers remain compatible

Add optional backend settings for the key (secret, excluded from repr) and model; validate presence at analysis time so AI configuration cannot prevent startup or existing map reads. Add empty placeholders to `.env.example`, pass both explicitly to the backend in Compose and never add `VITE_` key/model variables. Keep the model operator-configured and validate its Responses/function compatibility during the live verification path; do not hard-code an assumed model.

New dependencies are the official OpenAI SDK and Shapely, with the lockfile updated; frontend formatted text uses `react-markdown`. No migration is needed. Existing map GET responses, public resident submission, collection browsing and other admin layouts retain their contracts. The runtime-guide packaging changes affect backend builds and development mounts and must be checked in default and worktree Compose modes.

## Risks / Trade-offs

- [Model latency can consume the budget before synthesis] --> Use strict remaining-time limits, the synthesis reserve and explicit incomplete results; verify the configured model with a real multi-step run.
- [Broad catalogue increases initial context size] --> Keep descriptions and runtime guidance compact, generate shared metadata once and keep all payloads bounded. Verification reports request latency and tool-result bytes.
- [Point/polygon matching can be expensive over broad areas] --> Filter candidates in PostgreSQL, prepare geometry only on demand and respect query/run deadlines.
- [Optional data is sparse or derived mappings are stale] --> Separate live spatial membership from stored allocations and return coverage/unknown states; never rebuild during analysis.
- [Interpretation could conflate synthetic, estimated and observed data] --> Separate tools/scales, attach evidence labels and denominators and inspect the live answer for provenance.
- [Short snapshots can see changing data] --> Include per-query times and current-registry limitations rather than claim a frozen historical dataset.
- [Provider output is not guaranteed correct] --> Require tool evidence, expose missingness and leave final analytical prompt specialization to a later change; no output can trigger a write.
- [Map gestures conflict with selection] --> Capture drawing input above renderers, restore exact prior interaction settings and manually verify touch, cancellation and rotated views.
- [Repository-root image context exposes unrelated files] --> Use explicit COPY sources and root ignore rules; verify built images contain documentation and no environment files or exports.

## Migration Plan

1. Implement the map/sidebar and selection slice, then overview/registry/provider integration and the remaining analytical families in task order.
2. Update dependency locks, backend build context/document packaging and backend-only configuration; build and run the existing stack without AI credentials to verify map independence.
3. Load required development CSV exports only through the documented table-import command when collection data is needed. Before collection-data work, verify the configured directory has sites/bins/bin_hist exports; before any population rebuild verify the population GeoJSON. Stop and request missing inputs rather than using bin_sync. Optional derived reads do not require source files or rebuilds.
4. Run the local diagnostic and a configured live analysis, capture manual map/mobile/error/deadline evidence and verify default/worktree builds.
5. Rollback is a code/dependency/configuration rollback with no database migration or data rewrite. Removing the AI settings leaves existing map use available.

Live progress uses an opt-in `Accept: text/event-stream` response on the bbox-only endpoint. Events describe actual investigation rounds, tool categories and synthesis, followed by one result or safe error. The existing JSON response remains available. Disconnect cancels the run. Markdown uses GFM tables with raw HTML disabled; the separate raw timestamp line is omitted. Completed results hide the analysis action; incomplete results retain retry. Floating controls use opaque theme backgrounds.

Resident-request coverage remains available after a successful zero-row read. Empty counts mean no recorded resident requests for early emptying within the queried scope/period; query failure remains an error. The canonical resident-request dictionary and analytical guide explain this interpretation. Pending stage phrases vary across investigation rounds, hide counters and pulse in opacity unless reduced motion is requested.
