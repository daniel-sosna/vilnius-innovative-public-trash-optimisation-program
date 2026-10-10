# Proposal

## Why

Administrators need Vilnius waste collection service boundaries and zone names as geographic context in Žemėlapio analitika. Importing the supplied polygons into PostgreSQL makes this context available through the existing backend and independent map-layer lifecycle, without a runtime dependency on a local source file.

## What Changes

- Add `service_zones` storage and a migration, retaining only an identifier, name, integer zone number and reconstructable Polygon geometry in JSONB.
- Add a dedicated manual importer under `backend/app/interfaces/service_zones/`, following the existing executable-import convention confirmed during exploration. Its input is `service_zones.geojson` in the configured data directory, defaulting to `backend/data/`.
- Include the GeoJSON in `python -m app.interfaces.table_import` when present, with CSV and zone replacements committed together. A missing zone file produces a warning and preserves existing zones; the dedicated command fails when its input is missing or invalid.
- Serve a database-only GeoJSON FeatureCollection through `GET /map-analytics/service-zones`.
- Add the unchecked `Aptarnavimo zonos` option to the existing selector, with one translucent fill color, clear outlines and interior text labels using `zone_name`.
- Preserve simultaneous landfill, bin and population rendering, interactions, filters and map camera regardless of loading or enable order. Zone polygons and labels have no click interaction or clustering.
- Keep the current layout and legend unchanged. Explicitly exempt this visual context layer from mandatory legend entries.
- Exclude zone editing, popups, selection, per-zone colors, metric coloring, aggregation, new analytics legends, heatmaps, AI functionality and frontend source-file loading.

## Capabilities

### New Capabilities

- `service-zone-import`: Validate and atomically replace stored service zones from the supplied GeoJSON through a dedicated manual command.

### Modified Capabilities

- `table-csv-import`: Include an optional service-zone GeoJSON in the regular manual import transaction while preserving existing CSV discovery, replacement and partial-import behavior.
- `map-analytics`: Expose the stored service zones through a read-only map endpoint without request-time file access.
- `map-layers`: Add the independent visual polygon layer, label and interaction compatibility requirements, and the explicit exception for an empty service-zone legend.

## Impact

- Backend: new Alembic revision after current head `0013`, SQLAlchemy model, dedicated import CLI and shared connection-level import function; integration with `table_import`; map-analytics service, router and response schemas.
- Frontend: new service-zone loader and renderer registered in `mapLayers`; minimal ordering and point-interaction identification changes shared with the existing population renderer. No replacement of the map instance or clustering system.
- Data and documentation: canonical import filename, shared-directory setup, dedicated/regular command examples and repeatable verification instructions. Source data remains external and Git-ignored under existing conventions; executable code remains versioned and available in Docker.
- No PostGIS, new service, deployment or geometry dependency is planned. MapLibre polygon text placement is the initial label approach.
- Assumptions and uncertainties: the existing local `backend/data/serv_zones.geojson` is the supplied dataset (five CRS84 Polygons with the expected properties), to be provisioned under the canonical name. The configured shared directory currently has collection CSVs but lacks this file. Labels, opacity and boundaries require visual verification with all current layers, including tile boundaries and narrow screens; the five-feature count is a verification fixture, not a permanent importer restriction.
