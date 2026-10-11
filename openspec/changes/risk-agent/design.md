# Design

## Context

See proposal.md for motivation and the five delta specs for acceptance behavior. `container_adequacy.py` currently collapses labels by month and fits beta-binomial priors across the month's serving points. The generator, validator, importer, catalog, API schemas and frontend all assume complete months and monthly identities. Migration 0017 additionally requires `analysis.complete = true`; accepting partial periods therefore needs a new migration, not only JSON validation changes.

The map already consumes `projectDate` but only exposes it as a page attribute. Its adequacy hook independently selects catalog IDs; `useLayerSession` already caches by ID/revision and suppresses superseded results. Agent requests carry only bbox; the initial overview and strict registered tools run in bounded read-only sessions. Observation windows are based on actual run-start time. Existing spatial tooling uses Shapely without PostGIS. API containers exclude optional SciPy generation dependencies.

## Goals / Non-Goals

**Goals:** reuse offline preparation and database publication; make the cutoff a trustworthy artifact identity; preserve one analysis method and existing bounded model execution; provide a demonstrable preparation-to-map-to-agent slice.

**Non-Goals:** runtime generation, background jobs, changing other agent datasets' date semantics, forecasting overflow, training a new model, clipping population into a census estimate, adding general date ranges or changing the risk labels/colors.

## Decisions

### 1. Prepare all cutoffs in one explicit offline invocation

Extend the existing CLI with `--september-cutoffs`, mutually exclusive with `--month`/`--all-complete`, retaining required `--daily` and normal source overrides, policy and `--regenerate`. Validate source prerequisites before processing. Read the enriched CSV once; accumulate September evidence by day, waste stream and serving point and incrementally construct prefixes. Keep the existing complete-month path using the same fitting/classification functions.

Declare the September source cohort from September 1 calendar membership before building prefixes; validate every declared bin/day through each cutoff and reject undeclared bins within that interval. Record registry-only exclusions explicitly. Records outside the cutoff must not determine its eligible assessment cohort, counts or fitted parameters. Static registry eligibility, allocation, pressure and access references are built once and fixed for all cutoffs. For each prefix, fit the existing beta-binomial prior using only its labels, then classify using the existing sufficiency policy. September 1 can have insufficient evidence; do not lower thresholds or fabricate labels. Numeric instability must fail with an identified cutoff, not switch methods. Source fingerprints may cover whole files; numerical outputs must be independent of later labels.

Alternative: 30 full CSV scans or request-time generation. One scan supports the confirmed advance-preparation choice and avoids interaction latency. Publish validated files atomically and report each cutoff/reuse/failure, total duration and size. Import remains an explicit separate step; a partial preparation must not be reported as successful.

### 2. Extend identities and contracts while retaining completed artifacts

Retain `adequacy-YYYY-MM` / `adequacy_YYYY-MM.geojson` and schema/method version 1 for existing completed artifacts. New cutoffs use `adequacy-2026-09-DD` / `adequacy_2026-09-DD.geojson` and schema/method version 2. The new schema records exact inclusive bounds, static reference/policy identity, source coverage and existing provenance; `complete` means whole calendar month, so only September 30 is true. Calendar coverage is separately required to be complete for the requested interval. September 30's dated identity remains distinct from the legacy monthly identity.

Extend the shared validator, file discovery, importer, catalog schemas and TypeScript readers to support both shapes without weakening metric/geometry validation. Add an Alembic migration replacing the complete-only check with identity equality and a required JSON boolean completion flag; detailed period correctness remains enforced by artifact validation. Existing JSONB storage needs no feature table or new service. Imports validate the entire selected batch before atomically upserting exact IDs and preserving unrelated rows. Reuse and explicit regeneration policies apply to dated results as well.

Alternative: overwrite one September row repeatedly. Separate dated identities make reverse selection, caching and reproducibility straightforward and preserve completed results.

### 3. Resolve exact calendar cutoff in the catalog and map

Add optional validated `project_date` to catalog reads. Omission preserves legacy completed-only discovery. With a date, return earlier completed months plus the exact dated September result, ordered by effective period. No later result is eligible. Missing exact cutoff must be reported as missing, including when legacy full September is available. Artifact retrieval remains database-only and addressed by catalog identity/revision.

`useAdequacy` receives the shared date, keeps month/type selection, derives the exact September ID and refreshes the date-filtered catalog on each enable, catalog-error retry and relevant enabled date changes. Date changes while hidden perform no fetch; re-enabling resolves the current date before rendering. Initially prefer September; retain an explicit earlier-month choice across calendar changes. Keep the selected September state even if its artifact is missing. Do not present 30 independent dates in the month control. Show the actual interval and partial/full status in controls and replace the popup's month row with period. Cache exact identity/revision through the existing layer lifecycle and close its popup immediately on invalidation. Preserve other layers and camera.

Alternative: browser filtering an unfiltered catalog. Server date filtering centralizes period eligibility; frontend still guards late responses and exact-date matches.

### 4. Capture risk context without changing all analytical time windows

Require `project_date` in `AnalyzeRequest`; validate it before provider use and echo it in `AnalysisResponse` and streamed results. Store it in `RunContext` and the initial model context. Keep `started_at` for deadlines, real query timestamps and all existing non-adequacy period rules. Explain in evidence and model guidance that adequacy is September-to-date and service/request reads can have a different period. A frontend date-change effect aborts pending requests, clears answer/error and restores pending state while retaining the bbox; no automatic model call occurs. Compare captured date/request identity before accepting SSE results.

The agent resolves its own exact September artifact rather than receiving frontend rows, selected waste type or display-layer state. An earlier completed month selected for map display remains a comparison view; agent risk findings explicitly identify September-to-date. This preserves the existing visual-filter-independent scope. Requiring the date is a coordinated API break; update CLI checks and callers together.

Alternative: move every tool's default window to the demo date. That broadens this change into historical simulation behavior for service, requests, plans and timestamps; it is outside this risk integration.

### 5. Add bounded saved-evidence tools to the existing registry

Expose `get_adequacy_summary`, `list_adequacy_features` and `get_adequacy_feature`. All use the trusted run bbox/date and pinned artifact ID/revision, not model-provided dates. Summary accepts nullable waste type (null means all three separately); listing accepts nullable waste type/category and existing limit/offset semantics; detail accepts an internal stable feature ID. Register strict Pydantic schemas through the existing schema conversion and read-only dispatcher. Preserve the five-model-request limit, result budgets, per-query deadline, initial overview requirement and provider orchestration.

Discover exact saved artifact coverage in `get_area_overview`, pin its revision, and read only that artifact through the analytical session. Fetch or filter its stored JSONB features, apply exact Shapely bbox intersection with holes, omit invalid geometries with coverage feedback, and expose bounded summaries/pages without raw geometry. Retain external serving points referenced by matched polygons. Aggregate area counts by waste stream/category; full-polygon population estimates stay per stream and explicitly include whole intersecting polygons. Deduplicate assessment evidence and point capacity by `(waste_type, point_id)`; do not multiply observations across features or treat full point capacity as physical capacity within the bbox. Missing results, empty spatial matches, invalid parameters, revision replacement and query failures have distinct structured feedback. Pin absence too so a mid-run import cannot silently alter evidence.

Update domain guidance in existing `docs/agent-skills.md` and the runtime-marked part of `docs/data-model.md`; the Docker image already packages these. Describe source assumptions and link behavioral specs. Reuse the existing Responses API strict schema path; optional model parameters must remain nullable required fields with closed objects, per [official function-calling documentation](https://developers.openai.com/api/docs/guides/function-calling#strict-mode). Consult the documentation MCP again before implementation.

Alternative: prefetch GeoJSON into the prompt or let the model regenerate risk. Tool-led bounded reads preserve evidence budgets and read-only guarantees.

### 6. Enforce answer presentation at the response boundary

The sidebar has no manual catalog-refresh button. Re-enabling and enabled date
changes discover revisions; catalog errors retain a retry control.

The top-level Responses instructions impose two output rules: omit commentary
about synthetic/artificial/simulated data origin and include the exact Markdown
section `## Konteinerių pakankamumas`. Keep provenance in saved artifacts and
internal tool evidence, without relabeling estimates as recorded observations.
The section covers risk findings, period and uncertainty, or honest unavailable
or zero-match feedback. A deterministic backend guard rejects prohibited wording
and missing/empty sections. Rewriting uses the existing five-request/deadline
budgets; exhausted correction returns no answer with `response_policy` as the
incomplete reason. Both normal and SSE responses pass through this guard.

## Risks / Trade-offs

- Thirty geometry copies increase disk/database size -> retain portable self-contained artifacts, measure total bytes/import time and spatial latency; do not add normalization or a service without demonstrated need.
- Sparse prefixes can produce weak or unstable fits -> retain existing evidence criteria and explicit failures; verify the earliest cutoffs before claiming preparation complete.
- Synthetic association can sound causal -> tools preserve provenance, uncertainty, static-snapshot assumptions and candidate-action wording.
- Full polygons and external serving points exceed the selected rectangle -> clearly identify those scopes and deduplicate point evidence; never imply clipped resident counts.
- Changing date/revision during asynchronous reads can mix evidence -> exact keys, immediate invalidation, captured-date checks and pinned revision feedback.

## Migration Plan

1. Supply required registry exports, population GeoJSON and explicit immutable enriched CSV; install analytics extras only for preparation.
2. Deploy backend/frontend contract changes together and apply the additive constraint migration. Keep legacy completed artifacts and rows intact.
3. Run explicit September preparation with recorded inputs/policy; verify all 30 artifacts and import the set in one transaction. Reads remain usable with honest missing-data feedback before preparation.
4. Verify default September 14, first/last day, reverse selection, hidden layer, stale requests and a real agent investigation. Record commands, timings, output sizes and browser evidence in this change.
5. Rollback: stop the new callers, remove only new dated rows if necessary, then restore the previous constraint and application version. Preserve legacy rows/source files; do not downgrade the complete-only constraint while partial rows remain.
