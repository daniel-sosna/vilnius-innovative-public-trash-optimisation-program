# Tasks

## 1. Residential area and capacity calculation

- [x] 1.1 Add a pure analysis service and backward-compatible area-to-point mapping around `app.interfaces.bin_population.allocation`; verify existing point eligibility, coordinate grouping, distance tie-breaking and resident totals remain unchanged with the supplied exports.
- [x] 1.2 Calculate per-type point pressure, area-attributed capacity, access distance and unknown/suppressed/service-gap states; verify the 600-resident/3-m³ and shared 100/200-resident examples from the spec using a repeatable command, and verify resident/capacity conservation on the full snapshot.
- [x] 1.3 Calculate fixed snapshot pressure references and configurable access criteria; verify identical thresholds across requested months and report point outliers and excluded bins without modifying source files.
- [x] 1.4 Create `docs/data/container-adequacy.md` with analysis-environment setup, input prerequisites, snapshot/unit/access assumptions and links to the behavior spec; add its README documentation-index link and verify the documented paths and dependency installation.

## 2. Monthly fill analysis and GeoJSON publication

- [x] 2.1 Add optional backend `analytics` dependencies and stream the explicit enriched CSV into per-point/type/month counts and cohort/calendar coverage; verify NULL exclusion, level-4-only counting, duplicate/domain rejection and the June–September complete-month boundary without publishing October as complete.
- [x] 2.2 Implement the documented beta-binomial fit, conditional intervals, coverage rules, transparent categories and deterministic reason codes; verify optimizer convergence, valid posterior domains, insufficient/no-assessment behavior and deduplication of shared point evidence with a repeatable verification command.
- [x] 2.3 Add `python -m app.interfaces.container_adequacy` with month/all-complete selection, explicit inputs/policy options and regeneration controls; verify `--help`, actionable missing-data errors, unchanged source hashes, and deterministic results for one completed month.
- [x] 2.4 Publish validated canonical GeoJSON atomically under the configured data directory with period/schema/method/source metadata; verify identical-result reuse, refusal of changed-input replacement without regeneration, successful explicit replacement and preservation of the last valid artifact on failure.
- [x] 2.5 Extend `docs/data/container-adequacy.md` with actual CLI commands, output paths, options, optional dependency invocation, file transfer and regeneration side effects; add the README pipeline row and verify commands run as documented. Keep behavioral rules in the spec.

## 3. Saved analysis discovery and retrieval

- [x] 3.1 Extend map-analytics schemas and database-backed readers for the catalog and selected GeoJSON routes; verify valid discovery/retrieval works with source CSVs and allocation inputs unavailable after import, and catalog entries include period, provenance and content revision.
- [x] 3.2 Implement bounded analysis identity resolution and empty/error/unknown-ID behavior; verify empty table success, database read failures, 404 for unknown IDs and rejection of filesystem path identities.
- [x] 3.3 Verify a newly imported month and an explicitly reimported regenerated revision appear on subsequent catalog reads; update the offline-artifact paragraph in `docs/data-model.md` with the analysis output location, imported JSONB storage and a link to its operating guide, without restating API behavior.

## 4. Existing map and legend integration

- [x] 4.1 Add one stable `adequacy` layer definition and parameter-aware artifact loading/cache identity to the existing session lifecycle; verify pending-read sharing, revision invalidation, month-switch races, disabled-layer completion and no MapLibre instance recreation.
- [x] 4.2 Extend the existing polygon helper with data/feature-lookup replacement and topmost interactive polygon handling; verify analysis geometry and popups update together, point clicks retain priority and population interaction returns normally when analysis is hidden.
- [x] 4.3 Add Lithuanian month and single waste-type controls with an existing-style catalog-refresh button inside the current layer/legend card; verify latest-month/mixed defaults, session-preserved choices, local waste filtering, independent bin filters and unchanged camera during month changes.
- [x] 4.4 Render fixed category colors and compact analysis details with short category names, month/type, essential point/area metrics and one conclusion; retain coverage, uncertainty and provenance in the artifact; verify representative priority, ordinary, insufficient and service-gap areas and all-six-layer ordering at desktop and 320-pixel width.
- [x] 4.5 Update only the existing README map-analytics feature row to link the added capability; verify the frontend build and record manual UI evidence under this change rather than adding behavior descriptions to docs.

## 5. Integrated delivery verification

- [x] 5.1 Generate all eligible completed months from the retained source and inspect the imported artifacts through the running API/map; record actual output paths, input/result hashes, category/coverage summaries and generation/load timings in this change's verification record.
- [x] 5.2 Run the documented sensitivity comparisons for pressure quantiles, access distance and fill-evidence criteria; record affected resident/point counts and category changes, preserving the declared default parameters rather than silently retuning them.
- [x] 5.3 Repeat catalog refresh, month switching, layer hiding, failed-read retry and explicit-regeneration revision loading; verify completed files remain byte-identical during ordinary use, source files remain unchanged, stale selections never reappear and existing five datasets retain their interactions.
- [x] 5.4 Confirm the initial feature exposes completed-month analysis without a separate today selector, date-change trigger or partial-month claim; verify the deferred integration contract is retained in the spec/design and workflow follow-up before considering this change ready to archive.

## 6. Database publication and compact zone popups

- [x] 6.1 Add Alembic migration and ORM table preserving monthly GeoJSON structure and file revision; follow existing JSONB map-layer storage.
- [x] 6.2 Add an explicit validated GeoJSON import CLI with file/all selection and atomic upserts of selected months; preserve unrelated months and reject invalid batches before writes.
- [x] 6.3 Switch catalog and GeoJSON map routes to the existing database session; verify source-file independence, empty/unknown/error responses and revision changes.
- [x] 6.4 Shorten Lithuanian zone titles and popup content to seven essential rows and one conclusion; remove synthetic-data notices from popup and layer copy while preserving artifact provenance.
- [x] 6.5 Update docs/data/container-adequacy.md, docs/data-model.md and README command tables; verify migration/import/read behavior and frontend build/lint, recording evidence in this change.

## Workflow follow-up

- When the shared selected-today capability is proposed or implemented, include this integration in that change: generate the same analysis for month-start through the selected date inclusive, atomically publish and import a distinct partial-period GeoJSON, refresh this catalog/map, constrain availability to the shared date and guard against obsolete generation responses. Do not rewrite completed-month files. This dependency is deferred, not completed by the present tracked tasks.
- Archive this change after the implemented monthly slice and its verification evidence are accepted; retain the shared-date integration requirement in the durable capability spec so future work can discover it.
