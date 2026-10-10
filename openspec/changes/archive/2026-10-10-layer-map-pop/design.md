# Design

## Context

See [proposal.md](proposal.md) for motivation and the two delta specs for behaviour.

- This worktree currently registers only the landfill layer. Its existing `MapLayerDefinition` accepts general GeoJSON and provides independent renderer attachment, visibility and disposal. `useLayerSession` already implements lazy loading, request reuse, caching and retry; `AnalyticsMap` owns the persistent map, camera and shared popup; `MapLegend` accepts multiple labelled swatches per dataset.
- `PopulationCell` stores Polygon rings as JSONB, density, suppression, area and estimated residents. The allocation command stores suppressed source `<11` as null density with suppression true, applying a configurable density assumption to its estimate. Missing density stores null density and suppression false with a resident placeholder of zero.
- Map responses use `CollectionSession`, a repeatable-read/read-only snapshot with timeouts and rollback. The existing landfill service constructs GeoJSON from selected columns.
- Required data files and `.env` exist in this checkout. Native backend/frontend dependencies are not installed here. The earlier alternate-port stack on 5174/8001/5433 runs the other checkout and must not be mistaken for this worktree's runtime.
- Earlier source/database inspection found 14,079 polygons: 7,508 suppressed, 100 missing and the remainder numeric. Coordinates occupy roughly 3.37 MB. The missing-density remainder covers about 632 km² and contains 149 holes. These are snapshot measurements, not feature constants.

## Goals / Non-Goals

**Goals:**
- Expose stored data faithfully and reuse the existing layer lifecycle.
- Keep classification, legend and popup meaning consistent.
- Preserve point rendering and click priority independently of enable order.
- Verify code from this checkout in its own runtime.

**Non-Goals:**
- Add a new allocation model, geometry processing, migrations or automatic rebuilding.
- Make the separate bin-layer change a dependency or introduce a generic polygon framework before it is needed.
- Add viewport requests, vector tiles or interpolation without evidence that one cached source is unusable.

## Decisions

### 1. Serve a minimal projection of stored polygons

Extend `backend/app/interfaces/map_analytics/{router,schemas}.py` and `backend/app/services/map_analytics.py` with `GET /map-analytics/population-cells`. Select ID, coordinate rings, density, suppression, area and residents ordered by ID. Wrap rings in GeoJSON Polygon geometry without modifying coordinates, merged shapes or holes.

The response properties contain exactly four fields:

| Field | Numeric density | Suppressed density | Missing density |
| --- | --- | --- | --- |
| `density_per_ha` | Stored integer | null | null |
| `suppressed` | false | true | false |
| `area_ha` | Stored number | Stored number | Stored number |
| `residents` | Stored estimate | Stored estimate | null |

Project missing-density residents to null without changing storage, so the pipeline's placeholder zero cannot become a claimed population measurement. Include unknown polygons in the response for data fidelity, but exclude them from visible and interactive rendering.

Use existing `CollectionSession` and collection error handling. No file read or allocation rebuild occurs on a request. Empty stored data produces an empty collection; database failure remains an error.

**Alternatives:** serving the source GeoJSON bypasses stored rebuild assumptions; PostGIS is unnecessary for returning already stored rings. A join to `bin_population` would confuse bin locations with population catchments.

### 2. Use a dedicated population renderer through the current contract

Add `PopulationProperties` and a `FeatureCollection<Polygon, PopulationProperties>` loader in the frontend map API module. Register stable ID `population`, label `Gyventojų tankumas` and kind `polygon` in the current registry. A dedicated module under `frontend/src/pages/map-analytics/` owns presentation and attachment.

Create one unclustered GeoJSON source plus fill and subtle outline layers under `analytics:population:`. Both style layers filter to numeric density or suppression true. Merely making unknown polygons transparent is insufficient because invisible geometry can still capture interactions. The filter excludes the huge missing-density remainder and keeps its holes intact in the source.

Resolve popup data from the original cached features by ID, following the existing point renderer pattern. Implement `setVisible` and `dispose` without a new cache or session mechanism. Hiding closes only the population-owned popup; disposal removes listeners, layers in reverse order and then the source, and clears the cursor. Reuse the current shared popup for close controls and Escape handling.

**Alternative:** extend the point helper with polygon support. Rejected because the existing contract already permits a separate renderer and polygons do not use clustering.

### 3. Define the density scale once

Keep band thresholds, colours and legend labels together. Classify suppression into `<11`; otherwise classify the recorded numeric density. Never coerce null density to zero or classify by polygon resident totals.

| Density in gyv./ha | Proposed colour |
| --- | --- |
| `<11` | `#f2e5ff` |
| `11–49` | `#dac2ef` |
| `50–99` | `#b88bd9` |
| `100–199` | `#8d50b6` |
| `200+` | `#602080` |

Use 0.45 fill opacity and a subtle outline on known/suppressed polygons. Register the five entries with population identity and `gyv./ha` units through the existing legend, plus `Duomenų nėra (skaidru)` using a transparent bordered swatch. The legend remains available while unchecked, matching current screen behaviour.

**Alternatives:** quantiles would change category meaning with the dataset; a continuous heatmap would imply interpolation and discard source boundaries. Fixed bands provide stable interpretation.

### 4. Make render order and click ownership explicit

Insert fill/outline below the first existing analytics point layer; if no point layer exists, use the first basemap symbol as an insertion anchor, falling back to the end of the style when there is none. Point renderers append their layers, keeping later-enabled points above population. Where possible, also keep population below basemap labels.

Before opening a polygon popup, query rendered analytics point/cluster/count features at the click position. If a point marker owns the click, return and let its existing handler run. Otherwise open the polygon details at the click coordinates without changing camera. Do not rely on renderer registry order or delegated-event order.

Verify both enable orders with landfills. When bin changes are integrated, retain their filters, overlap groups, colours and asynchronous interaction handling; repeat the same precedence checks with bins without copying their implementation into this branch.

**Alternative:** appending the fill and relying on event order makes behaviour depend on which dataset finishes loading first.

### 5. Present source density and estimated totals separately

Build popup DOM through text content using the current popup pattern. Show the three rows in the delta. Use `Intl.NumberFormat('lt-LT')` for numeric density, area with at most two decimals and estimated residents with at most one decimal. Presentation rounding never modifies the response or storage.

For suppressed polygons the main density stays `<11`. For positive area, derive the estimate assumption from stored `residents / area_ha`, and explain `Skaičiavimui taikyta: X gyv./ha.` Format the derived value to at most two decimal places. Zero-area polygons receive an estimate explanation without division. Never hardcode the CLI default 5.

Include `Pagal deklaruotą gyvenamąją vietą. Gyventojų skaičius yra įvertis.` No source year or real-time population claim is added.

**Alternative:** substituting the assumed density for `<11` would make an estimate appear to be exact source data.

### 6. Verify this checkout on separate ports

Use a new Compose project `viptop-layer-map-pop` with separate named volumes and a temporary resolved configuration outside the repository. Resolve configuration from this worktree and ensure build contexts and bind mounts point here. Replace all published ports rather than appending mappings. Proposed frontend/backend/database host ports are 5175/8002/5434, checked available during planning; recheck before starting. Container ports and internal proxy/database hostnames stay unchanged.

Run migrations through the current backend startup, import all available CSVs using `python -m app.interfaces.table_import`, then run `python -m app.interfaces.bin_population`. Check table counts and every bin's allocation. `bin_days` is not needed. Record actual runtime configuration and verification URLs in the implementation verification guide. The earlier stack is a separate checkout and remains available to its existing work.

**Alternative:** repoint the earlier running stack. Rejected because it would replace the runtime used by the other worktree and could mix validation evidence.

## Risks / Trade-offs

- [Full-grid transfer and rendering] → Use one lazy cached GeoJSON source initially; record response bytes, initial load and pan/zoom responsiveness with real data before considering a different delivery approach.
- [Missing-density remainder captures clicks] → Filter it out of fill and outline layers, and verify its interior and holes in the browser.
- [Population covers point markers or replaces their popups] → Explicit style insertion and point-hit exclusion, verified for both enable orders.
- [Declared residence differs from actual presence] → Label declared residence and estimates in every popup; invent no source date.
- [Other worktree runtime produces misleading acceptance] → Separate project, source bind paths, volumes and ports; record evidence from this checkout's frontend and backend.
- [Concurrent bin change edits shared requirements/files] → Implement additively, preserve the current landfill colour, and reconcile complete selection/extension blocks when combining or archiving changes so neither population nor bin behaviour disappears. Treat initial-release exclusion clauses as superseded only for this feature's new population behaviour.
- [Nonempty response with only missing density] → Render no fabricated areas and retain the missing-data legend; preserve the existing distinction between a nonempty source, an empty response and a failed read.

## Migration Plan

1. Prepare this worktree's isolated runtime as described above; do not alter default-port mappings in the repository Compose file.
2. Add the endpoint and population definition/renderer. No schema migration or rebuild is needed solely to expose already stored polygons.
3. Verify the complete response against storage, through both backend and frontend proxy. Check numeric, suppressed and missing states, geometry and read-only behaviour.
4. Verify desktop and 320-pixel map behaviour, layer lifecycle, marker precedence and popup content. Run the standard frontend build and lint commands and record results.
5. Rollback removes only endpoint/renderer/registration additions. Stored population and allocation data remain available to existing consumers.
