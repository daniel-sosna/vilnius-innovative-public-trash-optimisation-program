# Tasks

Verification is assigned to the developer by explicit request. Codex performs
implementation only; unchecked tasks with implemented code retain their checkbox
until the developer supplies the verification described in that task.

## 1. Dated artifact contracts and storage

- [x] 1.1 Extend `adequacy_artifacts.py` validation/discovery for legacy monthly v1 and dated September v2 identities, inclusive bounds, month completion and period calendar coverage. Verify valid day 1/18/30 artifacts and rejection of malformed dates, identities, metrics and incomplete source coverage with the repeatable artifact audit.
- [x] 1.2 Add an Alembic migration updating the complete-only analysis constraint while preserving identity checks and requiring boolean completion. Verify upgrade with a legacy row, acceptance of valid partial rows and rejection of missing/nonboolean completion; verify rollback after removal of dated rows in an isolated database.
- [x] 1.3 Extend `container_adequacy_import` discovery and batch publication to exact dated IDs. Verify atomic rejection of a batch containing one invalid artifact, unchanged unrelated rows, idempotent reimport and explicit revision replacement.
- [x] 1.4 Update the schema/data storage section in `docs/data-model.md` for dated identities, versions and the completion/coverage distinction, linking the adequacy spec; verify descriptions agree with accepted generated metadata.

## 2. September advance preparation

- [x] 2.1 Add `--september-cutoffs` to the existing generator and implement one-pass September day evidence plus incremental prefixes using the existing fitting/classification method. Declare the source cohort from September 1 membership and validate every required prefix bin/day; verify CLI mode exclusivity and that future labels cannot enter counts or fitting.
- [x] 2.2 Add distinct atomic dated publication, cutoff/policy fingerprints and reuse/regeneration reporting. Verify 30 distinct September identities, correct completion flags, identical repeat-run bytes, unchanged legacy monthly files and preservation of prior valid outputs on failure.
- [x] 2.3 Extend `python -m app.interfaces.container_adequacy.verify` as a repeatable command for prefix metrics, sparse evidence, malformed coverage and no-future-leakage: change labels after a cutoff and compare counts, fitted priors, uncertainty and categories before/after. Verify exit codes and useful summaries; do not add an automated test suite.
- [x] 2.4 Update `docs/data/container-adequacy.md` with preparation/import commands, required inputs, output names/versions, source cohort assumptions and regeneration side effects; replace complete-month-only operational descriptions. Verify documented commands against CLI help and execution output.
- [ ] 2.5 Before real data processing, check the configured directory contains `sites_<digits>.csv`, `bins_<digits>.csv`, `bin_hist_<digits>.csv`, `population_density_1ha.geojson` and the explicit enriched daily CSV; stop and request missing sources. Prepare and audit all 30 real cutoffs, then import them in one transaction. Verify counts, source immutability, all dated rows and report preparation/import timings and total sizes in this change's verification evidence.

## 3. Calendar-driven map reads

- [ ] 3.1 Extend the catalog and map schemas with optional September `project_date` filtering and dual artifact versions/completion flags. Verify HTTP 422 for invalid dates, exact day 1/18/30 selection, no-date completed-only compatibility, exclusion of later results, and database-only retrieval after source files are unavailable.
- [ ] 3.2 Wire the shared date into `useAdequacy`, preserve earlier-month/waste choices and resolve the exact September result. Verify missing exact dates show missing-data feedback, hidden date changes do not fetch, re-enabling uses the current cutoff and rapid reverse changes cannot render stale geometry or popups.
- [ ] 3.3 Update sidebar and popup period labels with inclusive bounds and partial/full status while retaining the month/type controls and seven metric rows. Verify desktop/320-pixel rendering and keyboard use for day 1/18/30, with map camera, other layer selections and bin filters preserved.

## 4. Agent date context and saved risk tools

- [ ] 4.1 Consult the official OpenAI developer documentation MCP for strict Responses function schemas before implementing tool changes. Add required validated `project_date` to analysis request/context and echo it in normal/SSE responses; update frontend and CLI/check callers together. Verify invalid/missing dates fail before provider use and existing non-adequacy default periods and execution limits remain unchanged.
- [ ] 4.2 Add initial-overview adequacy discovery with a pinned exact artifact identity/revision or pinned absence. Implement read-only `get_adequacy_summary`, `list_adequacy_features` and `get_adequacy_feature` with typed filters, strict schemas, bounded output and exact bbox intersection. Verify polygon holes/boundaries, invalid geometry feedback, external serving points, controlled invalid detail IDs and deterministic default-50/max-100 pagination.
- [ ] 4.3 Implement per-stream category/population summaries and deduplicated `(waste_type, point_id)` assessment/capacity evidence with uncertainty, units, period and provenance. Verify three polygons sharing five level-4 assessments out of twenty report five/twenty once, unknown metrics stay null, full-polygon totals are labeled and streams are not combined as unique residents.
- [ ] 4.4 Extend the existing analytics-agent verification command for missing cutoff versus zero matches versus query failure, revision replacement and all risk tool contracts. Verify read-only execution and existing output/deadline budgets with useful exit codes; record spatial-query latency on the supplied data in this change.
- [ ] 4.5 Update `docs/agent-skills.md` and runtime-marked semantics in `docs/data-model.md` for dated saved adequacy evidence, assumptions and tool usage, linking the delta behavior specs as appropriate. Verify packaged agent guidance discovers the new tools and distinguishes risk periods from service/request periods; avoid duplicating behavioral contracts in docs.
- [ ] 4.6 Invalidate frontend pending/completed agent analysis on date change, abort/discard obsolete SSE responses and preserve bbox/map state. Verify changing the date during and after analysis clears stale answers/errors and does not invoke the provider automatically.

## 5. End-to-end acceptance

- [ ] 5.1 Run the preparation/import/catalog/map/agent slice for September 1, default September 14, September 18 and September 30. Verify map category/component evidence matches agent tool evidence for the same feature/date; verify agent access with hidden risk layer and different visual waste filters, and honest unavailable evidence when an exact cutoff is absent.
- [ ] 5.2 Verify rapid forward/reverse date changes, disable-during-load, cached re-enable, catalog revision discovery on re-enable and date-change-during-agent execution through the running app. Run the frontend production build and existing relevant verification commands; record commands, outputs, timing/size results and browser evidence in `openspec/changes/risk-agent/verification.md`.

## Implementation status awaiting developer verification

The implementation portions of 2.5, 3.1–3.3 and 4.1–4.6 are delivered. Their
verification portions and the end-to-end tasks 5.1–5.2 remain assigned to the
developer. See `verification.md` for the handoff, preparation/import outputs
and diagnostic commands. No additional verification is performed by Codex.

## 6. Answer presentation and controls

- [ ] 6.1 Remove the manual analysis-list refresh button, retain catalog-error retry and discover revisions on re-enable; developer verifies controls and cache behavior.
- [ ] 6.2 Add mandatory runtime answer rules and a backend guard for prohibited data-origin wording and a nonempty separate `Konteinerių pakankamumas` section, with correction within existing budgets and safe incomplete feedback; developer verifies normal/SSE and partial-answer paths.
- [ ] 6.3 Update `docs/agent-skills.md` runtime wording and change handoff for these presentation decisions; developer verifies rendered answers.
