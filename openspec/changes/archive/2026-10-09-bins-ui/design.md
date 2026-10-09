# Design

## Post-import activation (2026-10-09)

The user confirmed the data import is over and explicitly requested removal of
temporary Compose overrides and use of the real Compose setup. This supersedes
the import-period isolation/no-reload constraints for activation in this checkout.
Implementation was transferred into the main source tree. The temporary overrides
and runtime-path pointer were removed from both checkouts and the temporary
runtime directory. Real `docker-compose.yml` passes `VITE_MAP_STYLE_URL` with a
configurable Liberty default. Its existing database/volumes and normal backend
entrypoint are retained; no models/migrations/import changes were introduced.
The frontend dependency volume needs `npm ci` to install MapLibre before normal
application startup. At activation, Docker access was denied in the agent session,
so image builds/launch and live HTTP/SQL checks were not run by the agent. Current commands/evidence are in
`docs/collection-site-browsing-verification.md`; earlier evidence is in the
linked historical document. At activation, 8/23 tasks were complete; activation did not complete
any outstanding live check.


## Context

See `proposal.md` for motivation and `specs/collection-site-browsing/spec.md` for behavior. `backend/app/infrastructure/models.py` already defines Site, Bin and BinHist with the necessary columns. `bins.site_id` is indexed; the unique history index starts with `(bin_id, date, was_serviced)`. No collection HTTP interfaces exist yet. Trucks uses synchronous SQLAlchemy services, Pydantic responses, route-level sessions, and generic persistence errors.

Frontend routing and the shared navbar are in `src/App.tsx` and `components/layout/admin-layout.tsx`. `TablePagination` accepts page size and total, so it works for all three lists. Radix-backed `Dialog` already provides the modal shell. Trucks implements loading/empty/error markup, abortable requests, debounce and SVG overview styling; these are patterns to reuse, not existing generic components to assume. MapLibre and a chart package are absent.

The operational import must remain undisturbed. Compose bind-mounts both source directories and starts Uvicorn with `--reload`; edits in the main checkout can therefore reload the current server. `backend/start.sh` runs `alembic upgrade head` before serving. A new verification server must bypass that entrypoint, not merely override its command. Docker socket access was denied during exploration; live network/mount/runtime ownership remains a targeted verification preflight, not an assumption about running containers.

Main persistence specs are stale relative to source. Completed `update-data` defines the current physical-bin model, raw capacity assumption, derived site coordinates, and naive history timestamps. This design consumes that model; it does not change old requirements or archive previous changes.

## Goals / Non-Goals

**Goals:** Add a bounded, read-only SQL/API/UI path with explicit shared types; isolate code edits and verification from live mounts; reuse existing patterns with one small map component and simple charts.

**Non-Goals:** Generic repository frameworks, a new data-fetching framework, chart infrastructure, schema/index changes, generic map/navigation infrastructure, or automatic activation in the importing environment. Existing fleet behavior and backend startup files are outside implementation scope.

## Decisions

### 1. Extend the existing interface/service structure

Add `app/interfaces/sites/{router,schemas}.py`, `app/interfaces/bins/{router,schemas}.py`, and focused query services `app/services/sites.py` and `app/services/bins.py`. Register their routers in `app/main.py`. Use the existing application session factory; keep a dedicated browsing dependency rather than importing truck-specific exception handling. Translate missing parents into 404 and persistence failures into sanitized 500 responses without SQL or credentials.

All new endpoints are GET-only. Start each browsing transaction with `SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY` before any data query, and use local statement/lock timeouts to avoid unbounded reads (initial budgets: 5 seconds and 1 second). Do not alter database defaults or the engine/session used by the importer or Trucks. Close transactions promptly on response construction or failure. Read-only mode protects imported records even if an accidental write is later added to these services; one short snapshot keeps counts, items and percentages internally consistent while import commits concurrently.

Alternative: reuse the truck dependency or introduce a shared generic data layer. The former has truck-specific errors; the latter increases change scope. PostgreSQL's default READ COMMITTED can produce mismatched counts and items across queries during active import, so short repeatable-read snapshots are justified here. There is no snapshot shared across separate HTTP requests or pages.

### 2. Make the new API contract explicit

Browser requests use `/api/sites...` and `/api/bins...`; the existing Vite proxy strips `/api`. Backend routes have the following responses:

| Route | Response |
|---|---|
| `GET /sites` | `{items: SiteSummary[], total, page, page_size}` |
| `GET /sites/stats` | `{total_sites, total_bins, total_capacity_m3, bins_by_waste_type: WasteTypeCount[]}` |
| `GET /sites/{site_id}` | `SiteDetail` |
| `GET /sites/{site_id}/bins` | `{items: BinSummary[], total, page, page_size}` |
| `GET /bins/{bin_id}/history` | `{items: HistoryEntry[], total, page, page_size, successful_service_percentage, unsuccessful_service_percentage}` |

Define these fields in Pydantic and TypeScript together:

- `SiteSummary`: `id`, `address`, `bin_count`.
- `WasteTypeCount`: `waste_type`, `count`; keep the stored key unchanged, with translation only in UI labels.
- `SiteDetail`: `id`, `address`, `latitude`, `longitude`, nullable `sub_district`, `street`, `house_number`, `postal_code`, `bin_count`, `object_groups: string[]`, nullable `total_capacity_m3`, `waste_carriers: string[]`.
- `BinSummary`: `id`, nullable `inventory_number`, required `waste_type`, nullable `capacity_m3`.
- `HistoryEntry`: `id`, naive ISO `date` without offset, `was_serviced`, nullable `non_serviced_reason`, nullable numeric `fill_level`.

IDs and counts are JSON integers. Capacities and service percentages are JSON numbers or null, explicitly using numeric response fields rather than Pydantic's default Decimal-to-string serialization. Perform sums in database NUMERIC and convert only at the response boundary; no unit conversion or stored-value rounding occurs. Return an empty array for absent group/carrier collections and render it as `N/A`.

Pages default to 1; positive `page_size` defaults are 15, 10 and 20. A minor bounded-retrieval default is a maximum of 100 for sites and child bins; history has the required maximum 20. Reject invalid values with 422, rather than silently clamping. Positive missing parent IDs return 404, including child lists. Existing parents with no children return 200 with zero total. Oversized but valid pages return empty items and correct totals without overflowing SQL OFFSET. Place `/sites/stats` before the dynamic site route.

Alternative: send whole ORM trees or separate percentage requests. Explicit flat responses avoid lazy-loading history, keep payloads bounded, and let each history page and its aggregate share a snapshot. Existing truck response types are unchanged; backend schemas and frontend `pages/sites/api.ts` are the affected shared contract.

### 3. Use database pagination and set-based aggregates

For the site list, count Sites with the address condition alone. Fetch the ordered Site page with LIMIT/OFFSET first, then count bins for those IDs in a grouped query or page-subquery join. Do not join history or materialize all sites; include zero-bin sites. Escape `\\`, `%` and `_` before ILIKE, following the truck service's literal substring convention. A trimmed blank search has no effect. Site list order is `Site.id ASC` and child-bin order is `Bin.id ASC`.

For global statistics, count sites independently, compute bin count and `SUM(capacity_m3)` over Bins, and group bin counts by raw waste type. Do not aggregate sites through a child join that multiplies site totals. No address filter applies to this endpoint.

For details, retrieve the Site, select exactly one lowest-ID child for the four geographical text fields, and aggregate all child bins for count/capacity. Query distinct non-NULL object groups and carriers, with deterministic ascending text order. All first-child fields come from that child; never coalesce them with another bin's metadata. SQL SUM remains null if no known capacities exist, including zero-bin sites; counts are zero. Do not load a Site's ORM bin/history relationships.

For history, first verify the Bin exists. Use one aggregate over all `bin_id` matches for total, successful count and unsuccessful count. Fetch only the requested page, ordered `date DESC, id DESC`. With nonempty history, calculate `success = round(100 * successful_count / total, 1)` and `failure = round(100 - success, 1)` so displayed values total 100%; return null percentages for total zero. All stored statuses are required booleans. No-history is distinct from a bin with genuinely 0% success and 100% failure.

Alternative: derive summaries in the frontend, count children per row, or load ORM collections for sorting. Those approaches produce page-dependent totals, N+1 queries, or unbounded memory. Existing indexes are sufficient to try this design; use read-only plans and measured requests to identify actual problems, and report any requirement for schema changes instead of adding indexes.

### 4. Build three independent UI data paths

Add `pages/sites/` with the list, overview, details, history dialog and typed read helpers. Extend admin routes and the navbar while keeping existing truck operations and role selection; the shared pagination visibility rule also applies to Trucks. Keep sections structurally close to Trucks: restrained heading, three overview cards, one address input, rows with borders, and the existing pagination footer. Do not add CRUD controls.

The overview fetch is independent of list filters/pages. Use Trucks' 200 ms search debounce and AbortController/request-key pattern; reset page 1 on address changes. Details and paginated bins fetch separately so a bin-page failure does not blank the map and statistics. Retry each failed data area without repeating unrelated calls. Use existing last-page recovery when a response indicates a page is no longer valid because import changed the result set.

Site rows are full-row links with the external-link-style icon on hover and focus; they navigate in the current tab. Bin rows use keyboard-operable buttons to open `Dialog`. The dialog keeps its bin header, one horizontal successful-service percentage bar and bounded scrollable history; pagination remains reachable. Start history at page 1 for each bin/opening, abort requests on selection change/close, and restore focus to the triggering row. Desktop dialog width is about 1024 pixels, capped with viewport margins; constrain height with mobile viewport units. Each history entry uses four columns in one row. The history region scrolls horizontally on narrow screens and vertically for long pages while close/pagination remain reachable.

Reuse Buttons, Inputs, Labels, Dialog and TablePagination directly. Reuse loading/empty/error markup patterns locally rather than refactoring Trucks into a new generic component system. Chart values and labels remain readable as text. Use lightweight SVG for the waste-type donut and CSS/SVG for the successful-service bar, consistent with `TruckOverview`; a Recharts dependency is unnecessary for these fixed charts. Container total/category counts and the donut share one horizontal row. Glass is green (#15803d), paper/plastic blue (#2563eb), and mixed municipal waste brown (#92400e); unknown category colors remain deterministic. Category colors remain stable across requests. The shared TablePagination renders only for a known total greater than page_size, covering sites, bins, history and Trucks. The dialog omits its pagination wrapper for single-page results. No-bin donut and no-history chart have explicit empty states.

Alternative: a single page request containing all nested data would couple failures and inflate payloads; a new query/chart framework would add migration effort without a concrete need.

### 5. Centralize feature formatting and Lithuanian text

Use one small feature formatter for nullable text/numbers. Check null/undefined explicitly, never truthiness, so zero capacities, fill 0 and false statuses survive. The UI never prints JSON nulls; missing capacity displays only `N/A`, with numeric capacities suffixed `m³`. Known numbers use `Intl.NumberFormat('lt-LT')`, initially at most three capacity fraction digits and one service-percentage digit. Empty distinct-value arrays display `N/A`. Preserve postal codes and house numbers as strings.

History dates stay timezone-naive in the API. Format their date/time components without treating them as UTC or applying the browser's local timezone. Use `Data`, `Aptarnavimas`, `Neaptarnavimo priežastis` and `Užpildymo lygis`; service statuses are `Aptarnautas` and `Neaptarnautas`. Fill levels display raw 0–3 numbers.

Known source waste-type labels map in the UI only:

| Stored value | Display label |
|---|---|
| `Mixed municipal waste` | `Mišrios komunalinės atliekos` |
| `Paper/plastic waste` | `Popieriaus ir plastiko atliekos` |
| `Glass waste` | `Stiklo atliekos` |

Site statistics use `Seniūnija`, `Gatvė`, `Namo numeris`, `Pašto kodas`, `Konteinerių skaičius`, `Naudotojai`, `Bendra talpa` and `Atliekų vežėjas`. Preserve supplied addresses, inventory numbers, group/carrier names and historical reasons as source data; do not rewrite imported text or invent translated historical facts. If an actual unfamiliar value needs a Lithuanian translation, ask before assigning one. Keep `N/A` exactly as requested. Significant source-unit and coordinate assumptions belong in data documentation; the map omits the averaged-coordinate explanation at the user’s request; its data meaning remains documented.

Alternative: API strings such as `N/A`, truthiness fallbacks, categorical fill names and `Date(...Z)` would erase data distinctions or shift history time. Formatting stays a frontend responsibility.

### 6. Add a small configurable MapLibre component

Add `maplibre-gl` through npm with its lockfile, import its CSS, and use its Vite-compatible worker setup. Prefer direct MapLibre use over a React wrapper. A reusable `components/maps/location-map.tsx` accepts coordinate, zoom and interaction props; create/destroy the map in an effect, update the marker/center on site changes, and handle resizing and unmount cleanup. Site details pass `interactive: true`, zero initial bearing/pitch and zoom around 15.5. Enable drag, wheel/touch and keyboard movement/zoom; add MapLibre NavigationControl zoom buttons without a compass, with Lithuanian labels. Keep the marker at the stored coordinate and preserve attribution. This allows map exploration without adding route navigation.

Read the style from `import.meta.env.VITE_MAP_STYLE_URL`; put `VITE_MAP_STYLE_URL=https://tiles.openfreemap.org/styles/liberty` in `frontend/.env.example` and supply it to the separately started verification frontend. For native use, document the frontend environment file/startup; for packaged builds, supply it at build time. Current Vite runs from `frontend/` and has no `envDir`, so the root backend `.env` is not a frontend configuration source. Do not change the operator's root `.env` or permanent Compose configuration. Missing/invalid style configuration yields a Lithuanian map error, never a hardcoded style fallback in the component.

Keep required provider/data attribution visible and localize application-controlled map error/control labels. Map resource/WebGL failures stay within the map area; the Site and bins still render. NULL coordinates cannot place a marker; expose their missing value as `N/A` and avoid map initialization.

Alternative: hardcoded Liberty, a raster screenshot or future navigation abstractions would either break configurability or reduce the reusable map requirement. This component owns only map lifecycle and the currently needed marker.

References checked during exploration: [MapLibre options](https://maplibre.org/maplibre-gl-js/docs/API/type-aliases/MapOptions/), [OpenFreeMap setup](https://openfreemap.org/quick_start/), [Vite environment handling](https://vite.dev/guide/env-and-mode).

### 7. Isolate implementation and verification from the importer

Before editing application source, identify current source bind mounts through read-only runtime inspection and use an isolated checkout/worktree outside them. Source/package edits in the operational checkout are prohibited while they could trigger live reload. Planning-task progress may be recorded in the change directory without touching watched source. Do not copy implementation back into live bind mounts as part of verification.

Reuse the repository Compose definitions only through a temporary verification override with explicit unique names/project identity. Override build contexts/source mounts to the isolated checkout, use distinct dependency volumes/image tags and free frontend/backend ports, and attach only the new containers to a network that can reach the existing PostgreSQL service. Point the verification frontend proxy to its own backend. Do not start a second PostgreSQL server or mount `postgres_data` into any new container. Validate the resolved configuration before starting anything; confirm it has no operational source mounts, reused dependency volumes or migrations entrypoint.

Start only additional frontend/backend containers, using one-off `compose run --no-deps` semantics or an equivalently explicit dependency-free invocation. Override the backend image entrypoint to launch Uvicorn directly, without `/app/start.sh` and without migrations. New browsing endpoints enforce read-only transactions; verification uses only read requests and no truck CRUD or import commands. The new frontend receives the configured map URL on startup. Starting a new server is allowed; restarting/recreating existing services is not.

Check UI/API against existing committed records. For missing/NULL/fill 0–3 scenarios absent from operational data, browser-local mocked responses can verify presentation and must be labeled synthetic; use documented read-only inline query/formatter checks for non-UI logic. Do not create fixtures in the live database, even inside a rollback transaction, and do not migrate another database to satisfy verification. Record what was covered by real reads and what remains unverified; do not claim live coverage from a mock. Do not add automated test files.

The earlier Docker permission failure must not be resolved by changing daemon, socket permissions or restarting infrastructure. Check already available runtime access read-only; if no safe access exists, continue independent code/build work and report the verification access limitation. Stop only newly created verification containers by exact owned names if cleanup is needed. Never run a broad Compose down, remove or recreate PostgreSQL volumes, or remove shared networks.

Alternative: plain `compose up`, a command-only override, a new database, or source edits in the shared checkout risks service reconciliation, migrations, empty data or automatic reload. A separate project name alone does not isolate bind mounts, ports or database access, so all of these must be verified explicitly.

## Risks / Trade-offs

- [Counts/history change during import] -> Keep each response in a short read-only snapshot; use deterministic ordering and stale-request cancellation. Values across separate requests are best-effort committed views, not a frozen import snapshot; no polling or importer coupling is introduced.
- [Capacity source units remain unverified] -> Preserve raw numbers, display the requested `m³`, and document the inherited assumption without silently converting data.
- [Averaged Site location can differ from physical bins] -> Show the stored mean and identify it as derived; do not imply it is an entrance or navigation destination.
- [Read latency competes with import resources] -> Bound result sizes, avoid N+1/history joins and use finite local query timeouts. Measure reads against current storage and report schema-change needs rather than changing indexes.
- [Late responses confuse dialog identity] -> Key/cancel reads by bin, page and retry, reset on opening, and keep the selected bin summary visible.
- [Map assets or WebGL fail] -> Contain failure in the map, retain statistics/bin access and keep external attribution and Lithuanian error states.
- [Frontend environment is absent or changed after build] -> Document startup/build-time Vite configuration; verify the new server receives it without restarting the existing one.
- [Runtime access remains unavailable] -> Record the exact access error and unfinished live checks; do not claim verification passed or modify infrastructure to obtain access.
- [Archiving stale collection deltas restores obsolete contracts] -> Keep this change additive and merge `truck-ui`, then `update-data`, before eventual `bins-ui` archival under a separate request.

## Migration Plan

There is no database migration. Implement in the isolated checkout, install frontend dependencies there, and start only the newly configured verification application containers against existing read-only storage. Verify the whole browsing path, record results in a focused manual-verification document, and leave a reviewable implementation without applying source changes to live mounts while import could be interrupted. Activating code in the original environment is a later step after the import constraint is resolved, not part of automatic verification.

Rollback consists of discarding/reverting the isolated application changes and stopping only the owned additional application containers. Operational records and schema require no rollback because this change never writes them.

## Open Questions

- The exact accessible Docker endpoint, live database network identity and safe free verification ports are runtime facts to resolve during read-only preflight; absence of access limits execution but does not change the contract or planned architecture.
- Actual query timings and available examples of optional values can be measured during implementation without schema changes. Missing edge-case records require explicitly reported presentation mocks or coverage limitations, not operational fixture creation.
