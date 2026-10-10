# Proposal

## Why

Žemėlapio analitika currently offers bins, landfills and population density without named district boundaries. A selectable Seniūnijos overlay will provide geographic context for those datasets using the existing database-backed map architecture.

## What Changes

- Add `district_boundaries`, containing one named Polygon per imported seniūnija, and a dedicated manual importer under `backend/app/interfaces/district_boundaries/`.
- Use `backend/data/vilnius_seniuniju_ribos.geojson` only as backend import input, following the existing configured data-directory convention.
- Include district import in `python -m app.interfaces.table_import`, in the same transaction as selected CSV imports. A missing GeoJSON warns and preserves stored boundaries; a present invalid file fails the entire import.
- Add `GET /map-analytics/district-boundaries`, returning stored polygons and district names from PostgreSQL without runtime source-file access.
- Register an initially unchecked `Seniūnijos` layer with deterministic distinct vibrant colors, translucent fills and clear outlines without district name labels. The layer has no click or hover interaction.
- Extend the polygon renderer contract with styling, optional labels and optional interaction, and make ordering and point interaction priority independent of load order.
- Keep the current screen layout and existing legends; the district context overlay adds no legend entries.
- Exclude district name labels, popups, selection, editing, aggregation, metric coloring, heatmaps, grid layers and AI functionality.

## Capabilities

### New Capabilities

- `district-boundaries`: Manually import and persist the source district boundary catalog, with validation, repeatable replacement and source-file independence after import.

### Modified Capabilities

- `table-csv-import`: Discover the optional district GeoJSON alongside CSV exports, include it in atomic imports, preserve boundaries when absent, and report its outcome.
- `map-analytics`: Serve a minimal read-only district FeatureCollection from the database.
- `map-layers`: Offer Seniūnijos beside all existing layers, support polygon styling/labels/optional interaction, allow an empty legend for this context overlay, and preserve simultaneous rendering and interactions.

## Impact

- Backend: SQLAlchemy model, a new Alembic migration after the current head, dedicated importer CLI/parser, the existing table importer, and map-analytics service/router/response models.
- Frontend: API types/loader, district definition/color mapping, a focused shared polygon renderer and ordering helpers, and population interaction identification. Existing session loading and point clustering are reused.
- Documentation: source placement, native/container import commands and repeatable data/API/UI verification instructions.
- No PostGIS, separate deployment or import framework is needed. JSONB is already used for population polygons; the shared renderer supports district fills and outlines.
- Verified input: 21 uniquely named Polygons with unique `OBJECTID` and `NR`, 8,916 two-dimensional positions, closed counterclockwise outer rings and coordinates consistent with Vilnius. The supplied file is approximately 351 KiB and has no holes. Structural checks do not establish full polygon topology or an effective source date; neither is invented.
- Assumptions: the supplied file is the supported 21-district snapshot; its names define the initial centralized color mapping. Full topology repair, automatic reprojection and palette expansion for changed datasets are outside this change.
- Material verification risks: boundary visibility alongside population density and load-order independence. District name labels are excluded at the user's request.
