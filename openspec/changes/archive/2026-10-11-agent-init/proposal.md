# Proposal

## Why

Administrators can inspect map layers but cannot investigate a geographic area's operational data together. A full-screen map with area selection and a read-only AI analyst will connect geographic exploration to database-backed insights while establishing tools that later analytical prompts can reuse.

## What Changes

- Make `/admin/map-analytics` fill the viewport below the admin navigation, with floating layers and AI buttons controlling one responsive overlay sidebar.
- Move existing layer controls, waste-category filters and legends into a vertically organized layers panel while preserving map instances, camera state, caching, clustering and feature interactions.
- Add mouse/touch rectangular selection with confirmation, retake and cancellation, a persistent geographic bbox overlay, and an AI panel that retains selection and results when closed or switched.
- Add a backend-only OpenAI Responses API integration with strict function tools and a replaceable generic analytical instruction. The initial request contains the selected bbox, instructions, domain documentation and tool definitions, rather than database rows.
- Provide comprehensive typed, bounded, read-only analytics tools covering discovery, bins, sites, service attempts, resident requests, schedules, population/bin intersections, geographic context, facilities, cross-dataset investigation and global comparisons.
- Make stored synthetic bin-day outcomes and mock collection-plan predictions available optionally, with separate labels, scales and metrics.
- Start with the last 30 Europe/Vilnius calendar days including today; permit explicit investigation of older data. Analyze all database data within the bbox regardless of map visibility or waste-category filters.
- Limit each run to 60 seconds and five model requests total, reserving request five for synthesis. Report deadline exhaustion as incomplete analysis and retain selection for retry. Navigation and panel switching remain available while selection replacement and duplicate submission are disabled.
- Maintain runtime database/domain guidance and a central tool catalogue, plus a repeatable verification command and manual end-to-end evidence.
- Exclude free-form chat, predefined questions, session memory, database writes, AI map control, new predictions, route generation, web search and production MCP infrastructure.

## Capabilities

### New Capabilities

- `area-analytics-agent`: Geographic selection, the map's AI workflow, bbox-only analysis requests, bounded multi-step execution, analytical output and recoverable failure/incomplete states.
- `analytics-tools`: Read-only spatial discovery and composable analytical queries with explicit time, missing-data, provenance, population and comparison semantics.

### Modified Capabilities

- `map-analytics`: Full-screen map presentation, floating controls and one responsive shared sidebar replacing the below-map card.
- `map-layers`: Vertical sidebar controls and legends, with inline waste-category filters replacing the modal and preserving existing independent layer behavior.

## Impact

- Frontend: admin route layout, `MapAnalyticsPage`, `AnalyticsMap`, map styles, legend presentation and new selection/sidebar/analysis UI. Existing map GET responses and other admin screens retain their contracts.
- Backend: map-analytics router/schemas, an agent service package and local query tools, an OpenAI integration module, settings and backend-only Compose environment variables.
- Dependencies: official OpenAI Python SDK; Shapely for reliable polygon intersection and boundary-aware bin membership; `react-markdown` for formatted answers. Backend image builds package canonical runtime documentation from the repository root. No additional service, PostGIS migration or database schema change is planned.
- Documentation: extend `docs/development.md` for configuration and `docs/data-model.md` for agent-visible data meanings; maintain runtime agent guidance and registry-derived tool documentation. Update only the relevant README feature/index entries. Verification evidence belongs to this change.
- Assumptions: population intersection means locating selected bins in containing source polygons, not estimating residents clipped to the bbox. Site location and member-bin location are separate scopes. Current registry locations/carriers qualify historical aggregation; source capacity units remain an unverified m³ assumption.
- Material uncertainties: configured model latency and tool payload sizes may prevent synthesis within 60 seconds; incomplete results are an expected outcome. Available history, population allocations and synthetic plans may be absent or sparse; tools expose coverage rather than fabricate data. Provider retries must not bypass either execution limit.
