# Proposal

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


## Why

VipTop stores address-grouped collection sites, physical containers and service attempts, but administrators cannot browse them through the application. A complete read-only browsing slice makes the ongoing import useful and demonstrable, from citywide totals to one container's service history, without disturbing its data or execution.

## What Changes

- Keep container totals/category counts beside the donut; glass is green,
  paper/plastic blue and mixed municipal waste brown.
- Show pagination only when a list has more than one page, including Trucks.
- Allow map panning/zooming with localized zoom buttons; omit the on-screen
  averaged-coordinate sentence while retaining its meaning in documentation.

- Add `Šiukšlių surinkimo vietos` to the existing admin navigation, with `/admin/sites` and `/admin/sites/{id}` screens consistent with Trucks.
- Provide backend address filtering and pagination: 15 sites per page, 10 child bins per page, and at most 20 history entries per page.
- Display global site/bin counts, a bin-count donut by waste type, and summed capacity independently of the filtered site page.
- Show a interactive MapLibre location map, compact site aggregates, and location text from the child with the lowest internal `Bin.id`. Configure the style through `VITE_MAP_STYLE_URL`, initially OpenFreeMap Liberty.
- Open each bin in a wide dialog with single-row history entries containing its summary, one successful-service percentage bar calculated across all stored history, and newest-first paginated attempts.
- Display database NULLs as `N/A` throughout. Display stored fill-level numbers 0–3 directly, with `N/A` for NULL; preserve naive history wall-clock times.
- Handle loading, retries, empty results, missing parents, sites without bins and bins without history in Lithuanian, using existing admin and shadcn/ui patterns.
- Implement and verify from an isolated checkout while the operational import runs. Reuse Compose configuration for separate frontend/backend verification containers with distinct ports and dependency volumes, the existing database through read-only access, and an overridden backend entrypoint that runs no migrations.

Scope excludes database/model changes, migrations, fixture writes to operational storage, import changes or reruns, table resets, PostgreSQL volume changes, and restarts/reloads/recreation/shutdown of existing containers. Site/bin CRUD, routing, driver navigation, prediction and map editing are also excluded. Additional verification containers are the user-authorized exception to the original container restriction; this does not authorize changing the importing environment.

## Capabilities

### New Capabilities

- `collection-site-browsing`: Read-only administrator browsing of collection sites, their aggregates and locations, child containers, and container service-history summaries and pages.

### Modified Capabilities

None. This consumes the existing collection model without changing persistence or synchronization behavior.

## Impact

- Backend: add site/bin-history HTTP interfaces and SQL query services; register additive GET routes in `app/main.py`. Existing truck contracts, models and migrations remain intact.
- Frontend: add site pages and their typed API contract, bin-history dialog, reusable map and NULL formatting; extend existing routes/navigation and reuse `TablePagination` and `Dialog`.
- Dependencies/configuration: add `maplibre-gl` and its frontend lockfile entry; configure a frontend environment file/example and document style selection. Simple charts can use SVG/CSS like the existing fleet overview, avoiding another chart dependency. No permanent Compose or infrastructure changes are needed.
- Data assumptions: `capacity_m3` contains unchanged source volume; cubic metres remain the existing unverified assumption. Site coordinates are derived bin-coordinate averages, not surveyed entrances. Service percentages describe all currently stored attempts, which can be incomplete while import progresses; they are not predictions or evidence that the full source history has been imported.
- Material uncertainties: live Docker access was denied during exploration, so the actual import container, database connection, network and bind mounts must be inspected read-only before verification. Existing indexes support the planned query patterns, but actual query latency during import must be measured without adding indexes or changing schema. If access or safe runtime isolation cannot be established, report the limitation rather than altering operational infrastructure.
- Spec compatibility: main `collection-records` still describes the old model; completed, unarchived `update-data` contains the current `Site -> Bin -> BinHist` contracts reflected in source. This change builds on those contracts, introduces a separate browsing capability, and does not archive or rewrite either existing change. Future archival should merge `truck-ui`, then `update-data`, before this change.
