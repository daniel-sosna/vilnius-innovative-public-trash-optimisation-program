# Tasks

## 1. District catalog and standalone import

- [x] 1.1 Add the `DistrictBoundary` model and an Alembic migration after the current head, with generated bigint ID, unique district name/source identifier and full JSONB geometry; verify upgrade creates an empty table and an isolated downgrade leaves collection/population tables unchanged.
- [x] 1.2 Implement the dedicated parser and connection-based catalog replacement under `backend/app/interfaces/district_boundaries/`; verify the supplied file produces 21 unique records with unchanged names, all coordinates/rings and integer source IDs, and malformed/duplicate/projected/degenerate inputs fail before mutation.
- [x] 1.3 Add the standalone module CLI using `data_dir()` and `--file`, one transaction and source/count output; verify importing twice leaves 21 districts, a missing/invalid input exits 1 and preserves the catalog, and successful imports exit 0 without changing collection/population records.
- [x] 1.4 Document ignored source placement, shared-directory/container resolution and native/container standalone commands in README; verify the documented commands resolve the intended file and populate the catalog.

## 2. Regular import integration

- [x] 2.1 Extend table-import discovery to include the optional fixed-name district GeoJSON in the selected directory, warning when missing and rejecting competing district CSV/GeoJSON inputs; verify `--dir` precedence, missing-source CSV continuation, invalid/unreadable-source failure and dual-input rejection using isolated input directories.
- [x] 2.2 Integrate parsed district replacement into the existing CSV transaction without independent commits, supporting boundary-only input while preserving CSV discovery/reset/identity semantics; verify valid combined import commits both datasets, failures on either input preserve both previous snapshots, boundary-only import succeeds and neither input exits 1.
- [x] 2.3 Update the normal-import README section and repeatable verification instructions with district summaries, missing-file preservation and rollback/conflict cases; run the documented cases against an isolated database and record row-count/exit-code results.

## 3. Database-backed district API

- [x] 3.1 Add district FeatureCollection schemas, service query and `GET /map-analytics/district-boundaries` using `CollectionSession`; verify direct and proxied responses contain every stored ID in order, exact Polygon geometry and only `district_name` properties, including an empty successful collection.
- [x] 3.2 Add a focused read-only manual verification command under `app.interfaces.district_boundaries` following the existing population-check pattern, accepting explicit backend/proxy URLs and optional Host header; verify it independently compares SQL rows with all response IDs/names/rings, prints useful counts/bytes/timing and exits 0/1 for success/failure without credentials.
- [x] 3.3 Document endpoint and checker commands in README and district verification documentation; verify source-unavailable and source-changed-without-import reads retain stored data, and an isolated database read failure returns the existing HTTP 500 contract instead of file fallback or empty success.

## 4. Polygon overlay and existing-layer compatibility

- [x] 4.1 Add the focused shared Polygon helper with fill/outline styling, optional filter/labels and optional interaction; reuse it for population while preserving current density filtering, styling and detail formatting, and verify known/suppressed/missing-density behaviors plus population-owned popup cleanup through the running map.
- [x] 4.2 Add the narrow Polygon ordering contract/reconciliation and registered point-style identity helper; verify style-layer order is identical for both district/population attachment orders, existing point order is preserved, and district rendering cannot suppress population clicks or take priority over point interactions.
- [x] 4.3 Add the typed district API loader and registry definition with stable ID `districts`, label `Seniūnijos`, no legend entries, one centralized 21-name distinct palette without district name labels; verify all supplied names/colors, readable boundaries and absence of frontend source-file dependencies or district event handlers.
- [x] 4.4 Use the shared session lifecycle for all district rendering and tune translucent fills and outlines; verify initially unchecked/lazy loading, cached toggles, disable-during-read, empty/error/retry feedback, complete fill/outline hiding and unchanged map camera, bin filters and unrelated popups.
- [x] 4.5 Document the district enable/interaction/readability verification matrix, including all four layers, integer/fractional zooms and 320-pixel layouts; verify the delivered instructions cover point expansion/overlap groups, population clicks over district areas, existing legends and readable boundaries without district name labels.

## 5. Complete-system verification

- [x] 5.1 Run the frontend build/lint commands and meaningful backend import/schema/CLI checks without adding an automated test suite; verify the touched modules load, documented commands execute and build/lint checks pass, recording any pre-existing limitation separately.
- [x] 5.2 In an isolated running stack, first verify the configured data directory has the three required collection CSV exports and district source, then run the normal import and district response checker; verify the complete source-to-database-to-API-to-map path renders 21 districts with all existing datasets enabled and record the dataset counts and results.
- [x] 5.3 Exercise opposite enable orders and delayed responses, district toggles/loading/retry, bin categories/count groups and population details over districts; verify no map recreation, camera reset, stale visibility, incorrect click ownership or changes to existing legends, and record city/neighborhood/narrow-screen boundary readability.
- [x] 5.4 Verify a fresh API request and fresh map session still function with the source temporarily unavailable in the isolated setup, restoring it afterwards; verify a later invalid regular import rolls back both CSV and district changes while missing-source CSV import warns and preserves boundaries, and record the final results in district verification documentation.

## 6. District label removal

- [x] 6.1 Remove district name labels at the user's request while retaining fills, outlines, palette and session behavior; reconcile artifacts/documentation and verify the frontend build/lint and running map have no district symbol layer.

## 7. More visible district colors

- [x] 7.1 Make the district palette more vibrant and increase translucent fill and boundary contrast at the user's request; reconcile artifacts and verify the running map with districts alone and all datasets enabled, plus frontend build/lint.
