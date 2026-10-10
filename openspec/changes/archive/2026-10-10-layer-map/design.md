# Design

## Context

See `proposal.md` for motivation and the two delta specs for behavior. The current frontend already has nested admin routes, a responsive `AdminLayout`, same-origin `/api` proxying and MapLibre GL JS. `components/maps/location-map.tsx` demonstrates configurable styles, a bundled same-origin worker, Lithuanian controls, resize handling and map recovery, but owns a single DOM marker and is sized for site details.

The current checkout lacks landfill storage. The local `origin/main` reference at `db3ce5f` has `Landfill`, the three-record seed migration `0006`, nullable-details migration `0007`, and `/landfills`. These are implementation prerequisites, not new work for this slice. Only landfill ID/name are required; all three seeded records have coordinates. The user confirmed the three-record live catalog, while direct database inspection was unavailable.

## Goals / Non-Goals

**Goals:** Separate map lifetime, dataset lifetime and point rendering; deliver the real landfill layer through the existing frontend/backend; keep a small extension boundary that does not assume all geometry is a point.

**Non-Goals:** A generic GIS engine, dynamic plugin discovery, global caching, persistent map preferences, new deployments, changes to the site-detail map's behavior, or implementations of future analytical layers. Do not add omitted-coordinate metrics or operational validation workflows.

## Decisions

### 1. Build on the accepted landfill baseline

Before implementation, integrate the accepted main baseline containing the existing landfill code, retaining this change's artifacts and the project's current governance. Use the existing ORM mapping; add neither a duplicate model nor another seed/migration. Copying only a few landfill files would lose their existing contracts and dependencies, so use the accepted baseline as a coherent prerequisite.

### 2. Keep a separate analytics canvas and reuse the admin shell

Add the nested route and navbar entry. Put page-specific composition, API types and landfill definition under `frontend/src/pages/map-analytics/`. Put the reusable layer contract and point-rendering helper under `frontend/src/components/maps/`.

The page has a compact title and a map filling the content width and most of the available viewport height. Put one compact card below the map at every screen width: the `Sluoksniai` heading followed by labeled checkboxes, then the `Legenda` heading followed by color swatches and labels. Display dataset names without descriptive paragraphs; retain dataset meaning in registry metadata for later consumers. Cap the layer list height and allow internal scrolling for longer lists. Both sections stay visible on narrow screens. Suppress canvas focus outlines during pointer interaction; restore visible focus for keyboard interaction. Keep existing shell styling, navbar behavior and UI primitives.

Reuse the existing worker-bundling/configuration pattern and CSS. Read `VITE_MAP_STYLE_URL` without a component fallback. Leave the site's single-marker component intact except for a small shared setup extraction if genuinely needed. Making `LocationMap` accommodate all analytics state would couple unrelated lifecycles.

### 3. Use a small registry with renderer-owned lifecycles

The registry is an explicit collection of definitions, initially only `landfills`. Each definition supplies a stable ID, Lithuanian label, short dataset meaning, render kind, legend entries, loader and renderer configuration. Each legend entry is a color and Lithuanian meaning, independent of geometry. Selection lives in page state keyed by stable ID, not inside localized labels. A renderer attaches sources/style layers and event handlers, changes visibility and disposes its own resources.

Point definitions are constructed through the shared point helper, which always supplies clustering and expansion; definitions provide appearance, legend entries and popup content. Point appearance accepts native MapLibre color rules, including feature-property expressions for future waste categories, plus an optional uniform cluster color. The shared `Legenda` section lists every registered color meaning after the checkboxes in the card below the map, initially a green `Sąvartynai` swatch. Future non-point definitions use the same legend metadata with their own renderer. The contract also permits a non-point renderer to supply its own lifecycle. Do not implement a polygon/grid renderer, placeholder datasets or a generalized geometry-processing service now.

```text
Page selection --> Layer panel
      |
      v
Registry --> Loader/cache --> Renderer --> Persistent map
                                |
                                +--> Shared point helper --> Landfills
                                +--> Future non-point renderer
```

Active IDs and registry metadata remain readable by later in-app consumers. Loaded GeoJSON stays associated with its layer ID. This is sufficient context for a future assistant without adding assistant-specific APIs or UI.

### 4. Give the map and datasets independent lifetimes

Initialize the MapLibre instance once when the configured canvas mounts and hold it in a ref. Selection and data state must not be dependencies that recreate it. Add layer resources after style readiness, including layers selected while the style loads. Observe container size changes and call `resize()`; dispose the observer, events, popup and map on unmount.

Initially all layers are unchecked, a planning default following the requested enable-then-load flow. A page-scoped cache tracks each ID's idle/loading/ready/error state, successful data and in-flight request. First enable starts one read; toggles during that read reuse it. A late successful response is cached but rendered only if still selected. Once attached, hide/show a layer using its style-layer visibility rather than removing the map or refetching. Closing/hiding a layer closes its popup. Retry clears only that failed request state. On unmount cancel reads and ignore stale completions.

Use separate basemap and dataset error presentation. A dataset failure cannot become a whole-map failure. Intentional basemap recovery can rebuild the instance, retaining camera, selections and cached data and reattaching selected layers; ordinary layer toggles cannot rebuild it.

### 5. Use native clustering separately for each point dataset

Each point layer gets its own namespaced GeoJSON source with `cluster: true`, plus cluster-circle, count-symbol and unclustered-circle style layers. Start with `clusterRadius: 50` and `clusterMaxZoom: 14`; keep these shared defaults adjustable in the helper. Using one source per dataset prevents combined landfill/bin counts. No per-point React DOM markers or React cluster calculations are introduced.

Cluster activation calls the source's asynchronous `getClusterExpansionZoom(cluster_id)` and moves the camera toward the cluster. Guard the completion against disposal or deselection. Individual-point activation delegates to the definition's detail renderer. Use one current MapLibre popup with DOM/text content, a Lithuanian close label and the feature's actual coordinates. Distinct source/layer IDs and scoped handlers avoid cross-layer interference.

This follows the [MapLibre cluster example](https://maplibre.org/maplibre-gl-js/docs/examples/create-and-style-clusters/). Server clustering or additional clustering libraries would add complexity without benefit for this catalog.

### 6. Add a focused GeoJSON read projection

Create `app/interfaces/map_analytics/` router/schemas and `app/services/map_analytics.py`, registering the router in `app/main.py`. Reuse the existing short read-only `CollectionSession`. Select only ID, longitude, latitude, name, operator, address and coordinate quality from `Landfill`, ordered by ID. Omit rows when either coordinate is null; no accounting/reporting is needed for the three-record catalog.

New contract, used by the landfill loader:

| Element | Value |
| --- | --- |
| Backend route | `GET /map-analytics/landfills` |
| Browser route | `GET /api/map-analytics/landfills` |
| Response | GeoJSON `FeatureCollection` with `features` |
| Feature | `type: Feature`, numeric `id` from `Landfill.id` |
| Geometry | `type: Point`, `coordinates: [longitude, latitude]` |
| Properties | `name`, `operator`, `address`, `coordinate_quality` |
| Nullable properties | JSON null, displayed as `N/A` |
| Empty result | Successful response with `features: []` |

Return raw recorded property values; localize their presentation in the frontend. Use the existing generic database-error handling. There is no pagination, bounding-box query, detail request, authentication addition or new GeoJSON dependency. With three records a complete dataset is the simplest useful response. Preserve `GET /landfills`, which serves truck selection and exposes a different existing contract.

### 7. Localize presentation without rewriting the catalog

Use `Žemėlapio analitika`, `Sluoksniai`, `Legenda`, `Sąvartynai`, `Kraunami duomenys…`, `Nepavyko įkelti sluoksnio.`, `Duomenų nėra.` and `Bandyti dar kartą`. The facility name is the popup heading. Its only detail rows are `Operatorius` and `Adresas`; omit the repeated `Pavadinimas` row and the `Koordinačių tikslumas` row. The API retains recorded name and coordinate quality unchanged.

Provide a small landfill-specific presentation mapping for the three known seed descriptions. Suggested display names are `Ecoservice Gariūnų atliekų priėmimo ir rūšiavimo aikštelė`, `Ekobazės Lentvario atliekų tvarkymo aikštelė` and `Vilniaus regiono mechaninio biologinio atliekų apdorojimo įrenginiai (MBA)`. Translate the displayed English operator/address descriptions while retaining organization names, street numbers and qualification meaning. Coordinate quality is retained in the API but is not shown in the popup.

This is presentation for the known seed values, not a translation service or data migration. Proper names remain identifiable and the API/database retain original values. Unknown future source values can remain faithful source text pending that layer's own display rules. Popup content is recorded facility information, not an assessment of current intake capacity or route suitability.

## Risks / Trade-offs

- [Branch baseline differs from the inspected main reference] --> Integrate accepted landfill work first and resolve any concrete contract conflict before coding against it.
- [Only three points exercise clustering] --> Use their real nearby coordinates at several zoom levels; keep point behavior in the shared helper and verify reuse with a temporary in-memory definition, without adding another shipped dataset or modifying storage.
- [Style readiness or asynchronous reads race with toggles] --> Keep map readiness and latest selection separate; share pending reads and ignore stale completions.
- [External style/tile/glyph resources fail] --> Show a map-specific recoverable error; keep layer reads independent and require the configured style to provide the count-label font.
- [Source names and quality notes contain English] --> Translate known descriptive seed text at presentation time while preserving identity and qualifiers.

## Migration Plan

Implement against the accepted baseline with existing landfill storage already prepared. Add only application code, the route and documentation; this change creates no migrations and performs no import/reseed. Verify through read-only API requests and the real frontend. Preserve existing records, PostgreSQL storage and any running import when using development services.

Rollback consists of reverting this slice's navbar/route, map-layer code and new API registration. Existing landfill migrations, catalog endpoint and truck assignments remain part of the accepted baseline and are not rolled back with this feature.
