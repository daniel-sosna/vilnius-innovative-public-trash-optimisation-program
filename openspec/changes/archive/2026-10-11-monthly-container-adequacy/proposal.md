# Proposal

## Why

Administrators can view residents and containers on separate map layers but cannot identify residential areas with little available container capacity or see whether that pressure accompanies repeated level-4 fill assessments. Monthly, explainable area analysis will turn these datasets into comparable priorities that can be inspected on the existing map.

## What Changes

- Generate one self-contained GeoJSON analysis per complete calendar month, containing residential capacity pressure, access distance, level-4 assessment statistics, data coverage and explainable categories for each supported waste type.
- Reuse the population polygons as stable analysis areas and the existing nearest-residential-point allocation; evaluate mixed, paper/plastic and glass waste independently.
- Preserve completed results as files in the configured data directory. Explicitly import validated GeoJSON into PostgreSQL using the existing GeoJSON-import pattern; the map catalog and result routes read imported collections only. Map reads never generate or import analysis.
- Add one residential-adequacy polygon layer with month and waste-type selection inside the existing `Sluoksniai` / `Legenda` card below the map. Reuse established controls, Lithuanian presentation, popup styling, layer ordering and independent loading/retry behavior.
- Use short category names and compact popups with month/type, estimated residents, point container count, pressure/reference, distance, level-4 counts/frequency and one concise conclusion. Retain detailed uncertainty and provenance in GeoJSON metadata, without synthetic-data notices in the popup.
- Describe the shared selected-`today` integration as a deferred dependency. When that project capability is introduced, its implementation must also generate and publish month-to-date GeoJSON through the same pipeline and update this map. Do not introduce a competing clock or date selector here.

## Capabilities

### New Capabilities

- `container-adequacy-analysis`: Reproducible monthly residential adequacy calculations, explainable assessment categories, self-contained GeoJSON artifacts, preservation of completed months and the deferred month-to-date contract.

### Modified Capabilities

- `map-analytics`: Read-only discovery and retrieval of saved analysis GeoJSON, Lithuanian analysis details and month selection within the current analytics screen.
- `map-layers`: Residential-adequacy polygon rendering, analytical legend, waste/month selection and parameter-aware loading without recreating the map or changing existing layers.

## Impact

- Backend: an explicit analysis CLI/service alongside `app.interfaces.bin_population`; a JSONB-backed imported-analysis table, Alembic migration and explicit import CLI; database readers and schemas in the map-analytics API. No new service or model training is required.
- Frontend: `pages/map-analytics`, existing polygon-layer and session lifecycle helpers, and the existing shared layer/legend card. Existing endpoints and bin category semantics remain compatible.
- Data: immutable registry/population inputs and the enriched fill CSV; generated GeoJSON under the resolved data directory. The retained fill source spans June through October 9, so June–September are the initially eligible complete months; October is not a complete-month result.
- Material assumptions: residents use the nearest eligible residential point; registry/population attributes are static snapshots; capacity units are assumed to be m³; suppressed population uses the recorded estimate. Fill assessments are synthetic, concentrated on assessed/collection days and partly generated from resident pressure, so their association does not independently establish real-world shortage or causality.
- Exclusions: service-failure risk, forecasting, new ML training, street-bin/footfall analysis, route planning and implementation of the shared selected-`today` feature. Deployment integration of that future feature is a recorded follow-up dependency, not a background monitor.
