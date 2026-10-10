# Proposal

## Why

Administrators can inspect waste-related locations but cannot see where residents live around them. The stored Vilnius population grid can provide that context as a map overlay without a new data source or population model.

## What Changes

- Add an independently selectable `Gyventojų tankumas` layer to `Žemėlapio analitika`, using the existing grid polygons and merged cells rather than districts.
- Colour polygons with a translucent purple scale for residents per hectare. Fixed bands are `<11`, `11–49`, `50–99`, `100–199` and `200+`, with labelled legend entries.
- Clicking a displayed polygon opens a Lithuanian popup showing density, area and estimated total residents. Suppressed density stays `<11`, with the estimate assumption explained separately.
- Keep missing-density polygons transparent and noninteractive. Do not present the allocation pipeline's placeholder zero as a known zero population.
- Add a minimal read-only `GET /map-analytics/population-cells` GeoJSON response, using the stored population table, lazy loading and the existing page-session cache.
- Preserve the map camera and existing point interactions. Markers remain above polygons and receive overlapping clicks regardless of enable order.

## Capabilities

### New Capabilities

None; the existing map capabilities own this extension.

### Modified Capabilities

- `map-analytics`: Add the population polygon response, uncertainty semantics and labelled population popups.
- `map-layers`: Add the population overlay, density legend and polygon interactions alongside existing datasets.

## Impact

- Backend: extend the existing map router, schemas and service using `PopulationCell` and the read-only collection session. No migration, PostGIS or new dependency is needed.
- Frontend: extend the map API and registry, adding a dedicated population renderer and popup presenter through the existing layer contract. Keep the current map-first layout and controls/legend card.
- Scope: declared-residence density and stored estimates only. District aggregation, bin catchments, capacity pressure, interpolation, time filters and opacity controls are excluded. Do not change import or allocation behaviour.
- Confirmed choices: grid, colours plus popup, translucent purple. Design defaults: fixed bands above, 45% fill opacity, initially unchecked layer and Lithuanian numeric formatting.
- Current worktree: `/home/stitas/Projects/viptop-layer-map-pop`, branch `layer-map-pop`, currently contains the landfill layer and population tables; bin-layer changes exist separately and are not prerequisites. Main specs still restrict the initial release to landfills and exclude polygon rendering; the selection and extension requirements are deliberately updated here. Preserve existing landfill colour and clustering, and reconcile shared requirements if `layer-map-bins` is integrated later.
- Data/environment evidence: all mandatory CSVs, the optional schedule CSV and population GeoJSON are present in this worktree. Earlier import/rebuild produced 14,079 polygons, 21,951 bin allocations and approximately 544,476 estimated residents, including 7,508 suppressed and 100 missing density values. These snapshot counts are verification references, not API constants.
- Runtime limitation: the running isolated Compose stack on ports 5174/8001/5433 still mounts the other checkout. Implementation verification must run this worktree's code against an isolated database; that existing server is not evidence that this worktree's feature works.
- Material verification risks: full-grid response/rendering cost, preserving merged shapes and holes, excluding the large missing-density remainder from click targets, and preventing polygon popups from replacing point interactions. Stored coordinate data is approximately 3.37 MB; start with one cached GeoJSON response and measure the real system before adding delivery infrastructure.
