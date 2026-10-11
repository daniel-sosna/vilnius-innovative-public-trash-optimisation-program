# Proposal

## Why

The map's container-adequacy risk layer is disconnected from the shared September calendar, and the area agent cannot inspect its evidence. Preparing dated results in advance lets the map and agent explain the same September-to-date assessment without running expensive generation during interaction.

## What Changes

- Explicitly generate and import all 30 September 2026 cutoffs, each covering September 1 through its cutoff inclusive; exclude later assessments before aggregation and statistical fitting.
- Preserve completed-month artifacts and support separately identified dated artifacts, completion flags, revisions and coverage validation.
- Bind September risk selection to the shared calendar, filter out later results, show the actual period and handle missing results without substituting a later cutoff.
- Add bounded read-only agent summary and detail tools over saved adequacy geometry and evidence, with provenance, uncertainty and deduplicated serving-point counts.
- **BREAKING**: require `project_date` alongside `bbox` in the agent analysis request and echo it in the response. Date changes invalidate pending/displayed analyses without automatically invoking the model.
- Omit the manual analysis-list refresh button. AI answers must omit synthetic-data commentary and include a separate `Konteinerių pakankamumas` section; backend enforcement rejects noncompliant answers.
- Keep the agent's existing non-adequacy observation windows unchanged; its adequacy tools use the captured project date independently of map visibility and waste filters.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `container-adequacy-analysis`: advance preparation, cutoff-safe fitting, dated artifact identity and import.
- `map-analytics`: date-aware saved catalog, September selection and period presentation.
- `map-layers`: calendar-driven selection and stale-result handling.
- `area-analytics-agent`: trusted project-date context and dated risk investigation.
- `analytics-tools`: discoverable, bounded adequacy summary/detail reads with geographic and evidence semantics.

## Impact

Generation/validation/import under `backend/app/services/container_adequacy.py`, `adequacy_artifacts.py` and the adequacy interfaces; database catalog serving and map schemas; frontend adequacy hooks, controls, popups and analysis lifecycle; agent contracts, registry, queries, context and domain guidance. Extend the existing table's complete-only constraint through a migration and reuse its JSONB storage, read-only sessions, Responses API loop and spatial tooling; no additional runtime service or ML approach.

Assumptions: scope is September 2026; calendar selects risk cutoff, not forecast day; earlier complete months remain selectable; all three waste streams remain eligible for agent investigation regardless of display filters. Static pressure/access references retain their existing assumptions; evidence-based fitting uses only the requested cutoff. Material delivery uncertainties are preparation time, 30-artifact storage volume and spatial-tool latency within the existing agent limits; measure them during verification. Required source files must be supplied before data work.
