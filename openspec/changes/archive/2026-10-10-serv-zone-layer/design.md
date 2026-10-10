# Design

## Context

See `proposal.md` for motivation and scope. This design is needed because storage, two import entry points, the read API and native map rendering must form one complete path.

The branch already contains `PopulationCell` with JSONB polygon rings, a read-only `CollectionSession`, a population GeoJSON endpoint and a non-point `MapLayerDefinition` renderer. `useLayerSession` already implements independent selection, lazy reads, pending-read reuse, cache and retry; `AnalyticsCanvas` keeps the same map instance as selections change. No new layer lifecycle is required.

`table_import.load_tables` currently owns `engine.begin()`, truncation, CSV COPY, sequence adjustment and derived-table resets. Calling another standalone CLI after it commits would violate its all-or-nothing contract.

Data files are Git-ignored and excluded from backend image builds. Import code lives under `backend/app/interfaces/`, while Compose mounts the configured host data directory at `/app/data`. Exploration confirmed using that code convention rather than putting executable scripts under the data directory. The local supplied input is currently named `backend/data/serv_zones.geojson`; it contains five CRS84 Polygons. This checkout uses a shared data mount, which currently has the required collection CSVs but no zone file.

The population renderer identifies any `analytics:` circle or symbol as a point feature. A zone text symbol would therefore suppress a population click. Its layer insertion also depends on the first symbol layer, so simply adding another renderer does not guarantee stable area ordering.

## Goals / Non-Goals

**Goals:**

- Reuse existing database configuration, transaction handling, HTTP snapshots and layer registration.
- Keep file access confined to explicitly invoked imports and preserve the existing map instance and interaction ownership.
- Make repeated zone replacement and combined-import rollback predictable.
- Make the source provisioning and manual verification reproducible in native and Docker environments.

**Non-Goals:**

- Introduce PostGIS, spatial indexes, geometry reprojection, a new import framework or a separate service.
- Derive bin membership, population allocation or service metrics from these zones.
- Expand the layer contract into a general styling framework or change the existing screen layout.

## Decisions

### 1. Minimal independent storage

Add the next Alembic migration after `0013` and a `ServiceZone` model in `app/infrastructure/models.py`:

| Column | Representation | Meaning |
| --- | --- | --- |
| `id` | Integer generated identity, primary key | Internal feature identity |
| `zone_name` | Non-null text | Original `ZONA` value |
| `zone_number` | Non-null integer, unique | Original `ZONOS_NR` value |
| `geometry` | Non-null JSONB | Complete `{type: "Polygon", coordinates: ...}` object |

The full geometry object avoids requiring an implicit Polygon reconstruction convention. It differs deliberately from population storage, which holds rings only. Use nonblank-name and Polygon-object database checks alongside import validation. Do not add `OBJECTID`, source descriptions, bounding boxes, label coordinates or collection foreign keys. Internal IDs are not zone numbers and are not promised to remain the same after dataset membership changes.

JSONB is sufficient for a five-zone visual overlay; PostGIS would introduce operational work without a spatial-query requirement. Keep the supplied feature count out of the parser's rules so a later valid dataset can be refreshed without code changes.

### 2. Dedicated CLI plus a reusable connection-level writer

Create `app/interfaces/service_zones/{__init__.py,__main__.py,cli.py}` and a small module for parsing and replacement in that package. The parser reads and validates the entire FeatureCollection before writes. Validate Feature envelopes, properties, nonblank names, integer numbers (reject booleans), unique zone numbers, Polygon rings, finite two-dimensional positions, longitude/latitude bounds and ring closure. Accept absent CRS as standard GeoJSON longitude/latitude and the supplied CRS84 declaration; reject unsupported declared systems rather than guessing or reprojecting. Preserve all rings and original label values, discarding unrelated properties.

The dedicated command uses `--file`, defaulting to `data_dir() / "service_zones.geojson"`. It opens the existing engine transaction, applies the normal lock timeout, and invokes a writer accepting the active SQLAlchemy connection and validated records. That writer replaces zones only and never commits or creates its own engine. Deterministic insertion ordered by zone number and identity restart make repeated identical imports predictable; a transactional truncate/reload removes obsolete zones. An empty valid FeatureCollection replaces zones with an empty dataset, consistent with whole-dataset replacement.

Use existing logging and 0/1 exit conventions. A dedicated missing input is an error. Use safe exception reporting that does not expose database configuration.

Putting executable code in `backend/data/` was rejected with the user's confirmation because that folder is an external, ignored Docker mount. A separate import framework or shell orchestration would add complexity and duplicate existing behavior.

### 3. Optional zones in the normal import transaction

Extend the current `table_import` command rather than introduce another normal-flow entry point. Keep `discover_files` behavior and directory precedence. Independently discover only the canonical zone GeoJSON in that same directory. A missing GeoJSON logs a warning and does not replace zones through the zone importer; an explicitly selected service-zone CSV remains governed by the existing CSV contract.

Parse a present GeoJSON before opening the replacement transaction. Allow a GeoJSON-only run. Pass its validated records to the same connection used for CSV loading, truncation, derived resets and row counts. Avoid building an empty SQL `TRUNCATE` when there are no CSV-selected tables. Report zones along with CSV results only after commit. A present unreadable/invalid zone source is an error, not an optional-file skip.

Minor compatibility default: if both a discovered service-zone CSV and the canonical GeoJSON target the table, reject the run before writes with an explicit conflict message. This preserves generic CSV restoration without silently choosing a competing source; operators remove the unwanted source from the selected directory. Sequentially running two separately committed CLIs was rejected because it could leave updated CSV tables and stale or partially replaced zones.

### 4. Read-only API with a narrow response

Add a service-zone query in `app/services/map_analytics.py`, the `/service-zones` route in `app/interfaces/map_analytics/router.py`, and typed properties/features/FeatureCollection in the existing schema module. Reuse `PolygonGeometry` and `CollectionSession`; query ordered IDs and only the required zone fields. Return `geometry` from JSONB and properties `{zone_name, zone_number}`. No import module or source path is used by the request path.

Frontend `api.ts` gains the matching properties and loader, requesting `/api/map-analytics/service-zones` through the existing proxy. Treat empty features as successful empty data and read failures as layer-local errors. Retain current landfill, bin and population contracts unchanged.

### 5. Native polygon renderer on the current contract

Add `pages/map-analytics/service-zones.ts` and register a module-level definition with stable ID `service-zones`, label `Aptarnavimo zonos`, polygon kind and dataset meaning identifying waste collection service areas. Use `legend: []`; `MapLegend` already handles this without changing the UI. The spec deltas explicitly make this exception to the otherwise mandatory color legend.

The renderer attaches one non-clustered API-fed GeoJSON source and three uniquely namespaced layers: fill, line and symbol. Centralize visual values in the renderer: start with teal `#0f766e`, approximately 0.15 fill opacity, a darker clear outline and dark text with a subtle light halo. These are adjustable initial styling values; verification determines final opacity, outline width and zoom text sizes without changing geometry or color semantics.

Use `text-field: ['get', 'zone_name']`, the existing `Noto Sans Regular` font and native polygon point placement. The pinned MapLibre version's [symbol layout](https://github.com/maplibre/maplibre-gl-js/blob/v6.13.0/src/symbol/symbol_layout.ts) calculates a pole of inaccessibility for polygon symbols, so there is no need to introduce centroids, persisted label points or a geometry dependency. Labels can repeat on tile fragments at closer zooms; a globally unique label is not required. Use collision handling and zoom-dependent sizing/visibility and verify all five names at the initial city view and around tile edges.

`setVisible` changes layout visibility for all three layers; `dispose` removes layers before the source. Register no zone click, hover or cursor handlers and never call popup helpers for this layer. Leave React DOM labels, point helpers and clustering out of the renderer.

### 6. Small shared ordering and point identification helpers

Add a small map utility recognizing actual point layers generated by `pointLayerIds` (the `:points`, `:clusters`, `:counts` roles and corresponding circle/symbol types), rather than all analytics symbols. Reuse it in population hit checks and layer ordering so service-zone labels cannot suppress population details. This preserves future point datasets using the existing shared point renderer.

Normalize the known area/context layer ordering after renderer attachment in the map synchronization path. Move existing layers without recreating the map, and use present layer IDs rather than load order. Place the area/context group before the earliest appropriate basemap label or interactive analytics point layer, retaining basemap readability. Inside that group use this order:

```text
basemap geography
        |
        v
service-zone fill
        |
        v
population fill and outline
        |
        v
service-zone outline and text
        |
        v
interactive point markers and count groups
```

Putting zone outlines and names above the population shading keeps the boundaries readable; population clicks still work because zone visuals own no interaction. Preserve existing point rendering and popup priority. The utility only needs ordering for the current area/context layers and recognition of the existing point roles; do not add renderer registries, placeholder sources, new maps or broad layer-contract fields.

## Risks / Trade-offs

- [Shared mount hides local source] --> Provision the canonical file in the actual configured data directory, not just this checkout's `backend/data/`. Document the normal optional warning and dedicated error so absence is visible.
- [Source files are unversioned] --> Keep the supplied file external under current conventions; document its original name, five expected zones and property mapping. Do not bundle it into frontend assets or the image.
- [Native labels collide, disappear or repeat near tile boundaries] --> Verify the five names at the initial view, pan/zoom across tile boundaries and tune font size, halo, collision behavior and zoom limits. Do not promise one label per polygon at every zoom. If native interior placement cannot meet the accepted behavior, stop and revise the design before adding another placement approach.
- [Zone tint affects density colors] --> Put its low-opacity fill below population and verify readability of purple density bands; keep outlines and text restrained above shading and below points.
- [Point detection affects population interaction] --> Manually verify population clicks under zone labels and point/group clicks above population, with zone-first and zone-last loading.
- [Accidental partial import] --> Reuse the open CSV transaction and exercise invalid-zone and failing-CSV cases against an isolated verification database; do not chain standalone commands.
- [Validation is structural, not a topology repair system] --> Preserve supplied geometry and reject unsupported structures; do not introduce geometry repair or new spatial dependencies for this dataset.

## Migration Plan

1. Apply the new empty-table migration with the existing Alembic flow; no seed/import runs in the migration or at application startup.
2. Provision the existing supplied `serv_zones.geojson` as `service_zones.geojson` in the resolved data directory. Use the shared host directory for this worktree's Docker mount and retain the original input until the copy is verified.
3. Run the dedicated importer or normal manual import; verify five names, numbers and stored geometries. Before collection-data verification confirm the configured `sites_<digits>.csv`, `bins_<digits>.csv` and `bin_hist_<digits>.csv` exist; never fetch development data with `bin_sync`.
4. Verify API and proxy equality with stored rows, including reads when the source is unavailable, then verify the four-layer browser behavior and frontend build/lint.
5. Document exact commands and observed results in `docs/service-zones-verification.md` and add setup/usage instructions to README.

For rollback, remove/disable the new frontend definition and route before downgrading the migration. Downgrade drops only the new table; original collection and population storage is unaffected. Re-importing the retained source restores the zone dataset after reapplying the migration. Verification failures and temporary sources must use an isolated database/directory rather than altering shared developer data.
