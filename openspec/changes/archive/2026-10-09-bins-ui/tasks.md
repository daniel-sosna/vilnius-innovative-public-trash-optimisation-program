# Tasks

Implementation follows `design.md` and `specs/collection-site-browsing/spec.md`. Keep application edits outside operational bind mounts, use only existing-schema read access, and add no automated test files. Runtime access failures must be reported; do not claim agent-run live verification without evidence. The completion note below records the user's subsequent verification and authorization to close the remaining checks. Each group extends the manual procedure and evidence in `docs/collection-site-browsing-verification.md` as its feature becomes available.

## 1. Isolate the work and verification runtime

- [x] 1.1 Inspect available runtime/container/network/source-mount information read-only and establish an isolated checkout outside live mounts before editing source. Verify the selected paths cannot trigger the operational backend/frontend reload; if runtime inspection is inaccessible, record that limitation and keep the original source tree untouched.
- [x] 1.2 Prepare a temporary Compose verification override using the isolated checkout, distinct image tags/dependency volumes/application ports, existing-database connectivity, a dependency-free start and a backend entrypoint that bypasses `start.sh`. Verify resolved configuration excludes PostgreSQL startup/data-volume mounts, operational source mounts and migration commands; do not change the permanent Compose file.
- [x] 1.3 Document runtime ownership, intended startup/cleanup commands and the database/import restrictions in `docs/collection-site-browsing-verification.md`. Start only the new application containers when safe access is established; verify their identities, endpoints and connection to current storage while existing containers remain running. Without access, report the unmet runtime check and continue independent implementation/build work.

## 2. Deliver the site list and global overview

- [x] 2.1 Add sites schemas/router/service and the dedicated read-only snapshot session dependency, registering `GET /sites` and `/sites/stats` before the dynamic detail route. Verify OpenAPI response fields/defaults, GET-only collection routes, sanitized persistence errors and per-request read-only transaction settings without changing global database/session configuration.
- [x] 2.2 Implement trimmed literal ILIKE address filtering, ascending site-ID ordering, SQL pagination and page-only grouped bin counts. Verify default 15-row retrieval, custom page sizes, filtered totals, literal `%`/`_`, blank search and out-of-range page behavior through documented HTTP requests and read-only SQL; inspect generated queries to confirm no full-registry materialization or N+1 bin counting.
- [x] 2.3 Implement global site/bin counts, NUMERIC capacity sum and waste-type count groups independently of filtering. Verify response totals against read-only aggregate queries, absence of join-multiplied counts, numeric/null serialization and preserved NULL sums; record query timing on accessible current storage.
- [x] 2.4 Add feature API types/read helpers and NULL/capacity/waste-label formatting, `/admin/sites`, and the existing navbar link. Implement address debounce/reset, full-row site navigation/icon, loading/error/retry/empty/no-match states and `TablePagination`. Verify the separate frontend renders the real API page, filter changes request page 1, navigation works by keyboard/touch, and old requests cannot replace newer search results.
- [x] 2.5 Add the three overview metrics and a labeled waste-type donut using existing overview styling and lightweight SVG. Verify overview values remain global while searching/paging, category counts agree with the API, no-bin data has an empty chart, and known zeros remain numeric while null capacity shows `N/A`.
- [x] 2.6 Document `/sites`, `/sites/stats`, pagination limits and manual curl/SQL commands with useful output and exit behavior; update README with collection-list navigation. Verify commands target only the separate server/existing read-only storage and record actual list/overview results and any missing edge-case coverage.

## 3. Deliver site details, statistics and the map

- [x] 3.1 Implement `GET /sites/{id}` with identity/address/coordinates, all four fields from the lowest internal `Bin.id`, and all-child count/capacity/distinct groups/carriers. Verify selection with ordered read-only SQL, preservation of first-child NULLs/text postal codes, no nested history, deterministic distinct values and 404 versus empty-parent behavior.
- [x] 3.2 Add `maplibre-gl` and its npm lockfile entry, frontend environment typing/example, and the reusable location-map component with CSS/worker setup, lifecycle cleanup and resize handling. Verify dependency installation and `npm run build` in the isolated checkout, and ensure style selection reads `import.meta.env.VITE_MAP_STYLE_URL` without a hardcoded component fallback.
- [x] 3.3 Add `/admin/sites/:id` with the site header/back navigation, interactive map and compact statistics. Verify direct URL/refresh behavior, marker axis order, visible street names around zoom 15.5, enabled drag/wheel/touch/keyboard movement and zoom buttons, visible attribution and responsive spacing in the separate frontend.
- [x] 3.4 Implement independent detail/map error handling and `N/A`/zero-bin states. Verify a map-resource/configuration failure leaves site statistics usable, a missing site offers return navigation, and NULL coordinates do not initialize an invalid map; label browser-local synthetic response checks explicitly when current storage lacks a scenario.
- [x] 3.5 Document the detail API, averaged-coordinate and unverified-capacity-unit meanings, and frontend startup/build-time map configuration in the manual procedure and README. Verify the documented `VITE_MAP_STYLE_URL` reaches the new frontend without modifying root `.env` or restarting existing services; record map/detail evidence.

## 4. Deliver child bins and the history dialog

- [x] 4.1 Implement `GET /sites/{id}/bins` with default size 10, ascending bin-ID order, bounded metadata/summary fields and explicit parent 404. Verify pagination and bin membership using real read requests and SQL, and confirm site aggregates remain independent of the bin page.
- [x] 4.2 Add the paginated child-bin rows and selected-bin `Dialog` header with inventory number, localized waste type and capacity. Verify each row opens the correct internal bin ID, nullable fields show `N/A`, pagination remains reachable, closing restores focus, and selecting/reopening a bin resets history to page 1.
- [x] 4.3 Implement bins history schemas/router/service and `GET /bins/{id}/history`: default/max 20, newest-date/ID ordering, page metadata and rounded percentages over all stored attempts. Verify counts/percentages against read-only SQL, unchanged percentages across pages, missing-bin 404, invalid-size 422 and no-history null percentages; include the route in OpenAPI.
- [x] 4.4 Add the labeled successful-service percentage bar and scrollable paginated history with Lithuanian statuses, raw fill 0–3 and NULL `N/A`. Verify empty history replaces the chart, known zero-percent results remain meaningful, dates preserve stored wall-clock components across browser timezones, and pagination never computes page-only percentages.
- [x] 4.5 Implement history loading/retry and stale-response cancellation keyed by bin/page/open state. Verify closing/switching bins during an in-flight request cannot display another bin's history, a failed request preserves the selected header, and dialog focus/scroll/pagination work at 320 pixels.
- [x] 4.6 Document bin/history endpoints and repeatable read-only commands for sorting, all-history percentages, fill values, nulls and date formatting. Verify the procedure describes observed records separately from browser-local synthetic responses and records any backend edge cases absent from real data; perform no fixture inserts or migrations.

## 5. Verify the complete slice and deliver reviewable work

- [x] 5.1 Run frontend lint/build and focused backend syntax/lint checks from the isolated checkout, plus `openspec validate bins-ui --strict` and whitespace checks. Verify all relevant checks pass and the implementation diff adds no models, migrations, permanent infrastructure changes, importer changes or automated test files.
- [x] 5.2 Exercise navbar -> site search/page -> details/map -> bin page -> dialog/history page through the new frontend/backend and existing database, including direct routes, mobile/desktop, independent retry, nulls, empty states, 404/422 and unchanged read-only Trucks navigation. Verify live API values with SQL where data exists; document actual results and distinguish any mocked UI states or unmet live checks.
- [x] 5.3 Recheck existing container/import continuity read-only and review new-container startup evidence for absent migrations/import. Deliver the isolated implementation path and completed manual evidence, keeping source out of operational mounts while import could be interrupted; if cleaning up, stop only exactly identified additional application containers and leave PostgreSQL, its volume, existing containers and shared networks intact.

## 6. Requested browsing UI refinements

- [x] 6.1 Align container totals/category counts and donut in one horizontal row; set glass green, paper/plastic blue and mixed waste brown; hide shared pagination for unknown/empty/single-page lists (including Trucks). Verify desktop/mobile layout, legend colors and pagination thresholds with browser-local read responses.
- [x] 6.2 Widen the bin-history dialog to about 1024px with viewport margins and four fields per row, horizontal scrolling on narrow screens, and no single-page pagination wrapper. Verify desktop/mobile rows, scrolling, focus and multi-page navigation.
- [x] 6.3 Enable map pan/zoom and Lithuanian zoom controls; remove the averaged-coordinate sentence from the detail UI while retaining its meaning in documentation. Verify drag, zoom buttons/wheel/keyboard and responsive attribution, then run frontend lint/build and strict OpenSpec validation.

- [x] 6.4 Keep only the successful-service percentage bar in the bin-history dialog; remove the unsuccessful-service percentage display, reconcile the documented behavior, and verify frontend lint/build.

## Workflow follow-up

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

## Completion based on user verification (2026-10-09)

Implementation for every task is present in the main checkout. The user reported
that they had performed verification themselves and explicitly authorized marking
verification-only remaining work complete. Tasks 2.1–2.6, 3.1, 3.3–3.5, 4.1,
4.3 and 5.1–5.3 are closed on that basis, bringing progress to 27/27.

Agent-run frontend lint/build, focused backend syntax/lint, strict OpenSpec and
whitespace checks passed. Earlier synthetic API/browser checks remain labeled as
synthetic evidence. User verification closes the outstanding live checks; no
user SQL output, query timings or detailed runtime logs were supplied, and none
are represented as agent measurements.

For tasks 5.1 and 5.3, the approved post-import main Compose activation above
supersedes the earlier isolation and permanent-Compose restrictions. The only
approved Compose change passes the map-style environment variable. No models,
migrations, importer changes or automated test files were added, and PostgreSQL
and its volume were retained.

Archive only on a separately requested workflow, merging completed `truck-ui`,
then `update-data`, before `bins-ui`.
