# Design

## Context

See `proposal.md` for motivation and scope. The backend already stores population Polygon rings as JSONB and serves them through `app.services.map_analytics`, Pydantic response models and the read-only `CollectionSession`. No PostGIS extension is used. The regular `table_import` CLI discovers schema-named CSVs, runs replacement/reset operations under one `engine.begin()` transaction and reports committed row counts.

Frontend definitions register through `MapLayerDefinition`; `useLayerSession` handles lazy reads and caching, while `AnalyticsMap` attaches renderers to one map instance. Population currently implements its own Polygon rendering. Its point-priority predicate considers every analytics symbol a point layer. Its insertion anchor also assumes no other analytics polygon groups exist. These are concrete integration changes, not reasons to replace the map architecture.

The supplied source has 21 named Polygons, unique integer `OBJECTID` values 422–442 and unique `NR` values 1–21. It is 358,988 bytes with 8,916 positions. All coordinates are two-dimensional and consistent with longitude/latitude for Vilnius; no CRS declaration exists. All outer rings are closed and counterclockwise, with no holes in this snapshot.

## Goals / Non-Goals

**Goals:**
- Deliver one complete import/database/API/map path with no runtime source-file dependency.
- Share the existing transaction boundary and dataset lifecycle while making Polygon styling and interaction policy explicit.
- Preserve the current point clustering, population details, bin filters and responsive controls.

**Non-Goals:**
- Build a generic import framework, spatial query service or production boundary-management pipeline.
- Perform topology repair, automatic reprojection, metric calculations or district joins.
- Change the basemap, redesign controls, or add legend content. Product exclusions are listed in the proposal.

## Decisions

### 1. A small JSONB catalog with database-generated identities

Add a `DistrictBoundary` model and a migration after the current Alembic head (currently `0013`). Columns:
- `id`: generated bigint primary key, consistent with normal table-export identity handling.
- `district_name`: non-null text, unique, populated from `SENIUNIJA` without changing Lithuanian spelling.
- `geometry`: non-null JSONB containing the complete GeoJSON geometry object (`type` and `coordinates`).
- `source_object_id`: non-null unique integer from `OBJECTID`, retained for source identity validation and verification.

Do not retain `NR`, `SHAPE.area` or `SHAPE.len`; none is required for rendering or replacement. The complete geometry object differs deliberately from the population table's coordinate-only JSON: district API construction can return it directly, while leaving population storage unchanged. Identity remains internal to each database snapshot; repeat replacement need not preserve generated IDs, and color mapping never depends on them.

PostGIS and spatial indexes add no value to a full 21-row read. Using source `OBJECTID` as the primary key would couple database identity to one source and require special handling in the generic export importer; retaining it separately keeps the normal generated-identity convention.

### 2. Dedicated importer code beside the existing CLIs

Create `backend/app/interfaces/district_boundaries/` with a module entry point, CLI and focused parser/replacement logic. The user confirmed this location instead of placing executable code in ignored `backend/data/`. Input remains `vilnius_seniuniju_ribos.geojson` under `data_dir()`, respecting `VIPTOP_DATA_DIR` and the container data mount; `--file` overrides the standalone default.

The parser reads UTF-8 JSON and validates the full nonempty FeatureCollection before mutation. It checks Feature/property/geometry structure, nonblank district names, unique names and integer non-boolean source IDs, Polygon-only two-dimensional finite coordinates, longitude/latitude ranges, closed rings, at least three distinct ring vertices and nonzero signed ring area. Preserve all rings. Reject explicit unsupported CRS declarations rather than guessing a transform. This is structural validation, not a guarantee of fully valid topology. Do not reuse population allocation logic, whose density and area requirements do not apply.

The replacement function takes an existing database connection and parsed records; it owns neither an engine nor a commit. It replaces the entire district catalog and inserts the validated records. The standalone command supplies its own transaction and exits 1 for missing/invalid input or database errors, with a source/count summary on success. Full replacement follows the existing manual snapshot-import convention and removes stale rows without introducing upsert orchestration.

### 3. One transaction for the regular import

Extend `table_import` discovery to look for the fixed GeoJSON filename only in the directory selected by its existing `--dir` / `data_dir()` resolution. Parse it before mutation. Keep the existing collection resets, foreign-key rejection, CSV column handling and sequence handling.

Call the same district replacement function inside the existing `load_tables` transaction. Refactor the transaction contents only as needed to accept parsed district records and handle an import with no selected CSVs. Do not execute a subprocess or run a second independently committed importer: either could leave CSV and district data inconsistent after failure.

The agreed missing-file policy applies only to normal import: warn, preserve stored boundaries in the absence of either district input form, and continue selected CSV imports. An existing but unreadable/invalid GeoJSON fails the whole invocation. A boundary-only directory succeeds if the source is valid; neither input form retains the existing nothing-to-import exit 1.

Because CSV discovery automatically includes every application table, a district export can also be selected. Reject simultaneous district CSV and GeoJSON input before writes, reporting both paths. This explicit conflict rule avoids hidden precedence. With only the CSV export, use normal CSV semantics; with neither, preserve boundaries. Log committed district counts only after successful completion.

### 4. Reuse the map-analytics read contract

Add district properties/Feature/FeatureCollection response models reusing `PolygonGeometry`, a service selecting `id`, `district_name` and `geometry` in ascending ID order, and `GET /map-analytics/district-boundaries` on the existing router. Use `CollectionSession`; no file-path configuration or importer is involved in the request path.

Response example:

```json
{
  "type": "FeatureCollection",
  "features": [{
    "type": "Feature",
    "id": 1,
    "geometry": {"type": "Polygon", "coordinates": [[[25.2, 54.6], [25.3, 54.6], [25.3, 54.7], [25.2, 54.6]]]},
    "properties": {"district_name": "Žirmūnai"}
  }]
}
```

These example coordinates illustrate the contract, not the source boundary. The frontend loader requests `/api/map-analytics/district-boundaries` through the existing proxy and checks the response shape. Empty tables return an empty successful collection; SQL failures follow the existing HTTP 500 contract. No source metadata, label coordinates, palette values or derived statistics need API exposure.

### 5. Shared Polygon rendering with explicit optional behavior

Introduce a focused `createPolygonLayer` helper under `frontend/src/components/maps/`, alongside the existing point helper. Its definition accepts fill/outline styling, an optional filter, optional symbol-label layout/paint and optional feature-details interaction. It returns the existing visibility/disposal lifecycle and never clusters. Disabled interaction registers no click, enter or leave handlers and does not change cursor or close another layer's popup.

Register districts as stable ID `districts`, label `Seniūnijos`, kind `polygon`, with labels omitted, interaction disabled and `legend: []`. The existing checkbox rendering and session hook need no special district state. Move the population renderer to the shared helper while preserving its current filter, density palette, opacity and details formatting; only its attach/lifecycle and point-priority identification change. Point renderers retain their grouping logic.

Add a narrow shared point-layer identity predicate based on registered point-layer IDs from `pointLayerIds`, including points, clusters and counts. Use it for polygon click priority instead of testing for every analytics symbol. Polygon rendering therefore never suppresses population details as a point interaction. Resolve feature details from the original response as population does today, retaining properties and holes.

### 6. Explicit polygon ordering independent of attachment timing

Extend the shared definition/renderer contract only with the ordering information needed here: a Polygon order value and its rendered style-layer IDs. Districts have a lower order than population. After a Polygon renderer attaches, reconcile all attached Polygon groups in bottom-to-top order before the earliest existing point style layer or basemap symbol anchor. Within each group, order fill, outline, then optional names. Exclude analytics labels when identifying a basemap symbol anchor.

The resulting analytics order is district fill/outline, population fill/outline, then existing point circles/counts, with basemap labels kept above area fills where possible. Reconciliation moves existing layers; it does not rebuild sources or the map. Leave the existing relative order of point datasets untouched. Hidden Polygon renderers retain their order, so toggling requires visibility changes only.

Relying on registry order or the first symbol alone would fail when responses complete in another order or when another analytics symbol becomes the first symbol. Avoid fixed basemap layer IDs because the existing style is configurable.

### 7. Central district colors without name labels

Define one explicit name-to-color mapping for the source's 21 district names in the district definition module. Use unique saturated palette entries and a MapLibre match expression; do not assign by array position, generated IDs or hash modulo a small palette. The names are the supported snapshot: changed source names require deliberate mapping review. Colors distinguish identity, not a metric.

Use 0.32 fill opacity and a fully opaque 1.8 px outline. This increases district contrast at the user's request while keeping streets visible and preserving population styling. Per the user's follow-up, districts omit the shared helper's optional label configuration and attach only fill/outline layers. District names remain in storage, the API and the centralized palette for identity; the overlay displays no district name text. The shared helper's optional label support remains available to other definitions.

## Risks / Trade-offs

- [District colors can tint population shading] → Keep district fills translucent, population above districts and verify the combined map without altering the population density scale.
- [Population fills can reduce district outline contrast] → Use appropriate line contrast; verify all layers together at city and neighborhood zooms while retaining the specified order.
- [Shared Polygon extraction can alter population behavior] → Preserve current filters, popups and properties, verify missing-density noninteraction and marker priority, and limit extraction to rendering/lifecycle code.
- [Optional missing source can leave an empty district catalog] → Warn during normal import, retain the existing empty-layer feedback and make the dedicated import command/documentation clear.
- [Ignored input is not bundled into Docker images or Git] → Document host/shared data placement and the existing `/app/data` mount; runtime reads remain available from the database after import.
- [Two input forms can target one table] → Reject simultaneous CSV and GeoJSON before mutation; support the existing export path when it is the sole district input.

## Migration Plan

1. Add the model/migration and apply it to the development database. Creation leaves the catalog empty and imports nothing automatically.
2. Confirm the configured directory contains the supplied GeoJSON and required collection CSV exports before exercising the combined flow. Use CSV import, never VASA synchronization, for development collection data.
3. Run the normal import or the standalone district command. Verify 21 stored records and source names/geometry, then verify the API directly and through the frontend proxy.
4. Verify the map with all layers, both enable orders and delayed responses, visibility/caching/error behavior, point/population interactions, boundary readability and narrow layouts. Record repeatable commands and observed results; add no automated test suite.
5. Verify API/map availability with the source temporarily unavailable in an isolated setup, then restore it. Verify invalid-input rollback and missing-source continuation without modifying shared datasets.

Rollback removes the frontend/API feature before downgrading the district-table migration. Downgrade drops only the district catalog; CSV collection data and population tables remain intact. Restoring an earlier boundary snapshot uses an explicit import.
