# Design

## Context

See `proposal.md` for motivation and the two delta specs for observable behavior. The current frontend registry has one stable definition, `landfills`, and `useLayerSession` already supplies lazy loading, pending-read sharing, successful session caching and per-layer recovery. `AnalyticsCanvas` creates one map; its synchronization method attaches each renderer once and thereafter calls only `setVisible`.

`createPointLayer` owns a namespaced GeoJSON source, cluster circles, counts, individual circles, delegated events and disposal. It supports property-based point colors, but has no data-update hook. It captures original features by ID to preserve null popup values. All layers currently use radius 50 and clustering through zoom 14. Landfill cluster color inherits its individual color. The installed MapLibre source exposes `setData`, `getClusterLeaves` and expansion zoom; the map defaults to maximum zoom 22, while a GeoJSON source defaults to maximum zoom 18.

The backend already has a `/map-analytics` router, GeoJSON response schemas, a seven-column landfill projection and a bounded read-only `CollectionSession`. `Bin` supplies the requested fields; inventory and capacity are nullable, capacity is numeric, and waste type/coordinates are non-null in the current schema. Exploration's database snapshot contained 21,951 bins and extensive coordinate sharing; see the proposal for the observed counts. Source data is recorded registry data, not predictions or surveyed locations.

## Goals / Non-Goals

**Goals:**

- Preserve independent dataset loading and one map instance while allowing a renderer's source data to change.
- Use one MapLibre clustering engine and one display source per point dataset, with bin-specific configuration and interaction hooks.
- Keep cached API data authoritative, category state separate from main visibility, and rendered membership synchronized with filters.
- Make every bin in a high-zoom overlap group individually reachable with bounded, accessible popup layout.

**Non-Goals:**

- A generic filtering framework, a second source for overlapping bins, or per-bin React/HTML map markers. The requested collision merge extends native bin clustering rather than introducing a competing fallback.
- Reworking site-page categories, persistent browser storage, viewport-based backend queries, fresh data polling or a global cache.
- Changes to landfill detail content, APIs or clustering/expansion semantics beyond its inherited black color.

## Decisions

### 1. Project the existing bin table directly into GeoJSON

Extend the existing map router/service/schemas with `BinProperties`, a bin feature/collection and the existing `PointGeometry`. Query only ID, longitude, latitude, waste type, inventory number and capacity; order by ID, omit unusable coordinates defensively, and serialize capacity as a number or null. Return feature ID at top level, geometry coordinates once, and exactly the three properties below:

```text
GET /map-analytics/bins
  FeatureCollection
    Feature.id = Bin.id
    geometry = Point [Bin.longitude, Bin.latitude]
    properties = { inventory_number, waste_type, capacity_m3 }
```

Use `CollectionSession` as for landfills. The frontend reads `/api/map-analytics/bins` through the existing proxy with an abort signal and lightweight response validation. Register a stable `bins` point definition alongside `landfills`.

**Rationale / alternatives:** Existing browsing endpoints paginate and/or include different fields; repeated paging and frontend reshaping would complicate complete clustering. The direct projection avoids loading relationships or histories and needs no migration, import or dedicated category request.

### 2. One bin category mapping drives filtering and presentation

Add a map-analytics-local category module with exact observed source keys, stable category IDs, labels and colors:

| Source key | UI label | Color |
| --- | --- | --- |
| `Paper/plastic waste` | Popieriaus ir plastiko atliekos | `#2563eb` |
| `Glass waste` | Stiklo atliekos | `#15803d` |
| `Mixed municipal waste` | Mišrios komunalinės atliekos | `#92400e` |
| Any other string | Kitos atliekų rūšys | `#6b7280` |

Use this mapping to generate the MapLibre point-color expression, localized detail/list text, filter category classification and legend entries. Do not guess alternate database strings or rewrite source values. Keep all three known controls available; show one fallback control only if the loaded data contains unexpected strings. The fallback selection starts true even before it becomes visible. A uniform `#64748b` count color has the separate legend label `Konteinerių grupė`. Set the existing landfill color constant to `#000000`; its cluster and legend inherit it.

**Rationale / alternatives:** The known labels/colors already match site overview presentation. Localizing unknown values as one fallback category honors the confirmed behavior and prevents raw unfamiliar English text from leaking into the interface. A shared global category refactor is unnecessary; arbitrary cluster category colors would incorrectly imply one waste type.

### 3. Separate cached data, filters and rendered data

Keep `useLayerSession` as the owner of unfiltered responses, requests and main selections. Own bin category selections in a separate page-lifetime state/hook initialized with all categories true. Main layer toggles do not modify it. Refresh/leaving and reopening the page creates a new session; neither localStorage nor server persistence is added.

Memoize the bin FeatureCollection derived from the loaded bin data reference and category selections only. Reuse the original feature objects; return the original collection when all categories match, and a stable empty collection when none match. Optionally index categories once when data arrives to avoid repeated classification. Changes to map position, modal visibility, other layer state and main visibility must not rerun filtering.

Add optional `setData(data: LayerData)` to `LayerRenderer` and an optional per-ID rendered-data map to `AnalyticsMap`/its runtime synchronization inputs. A point renderer implements `setData`; non-point or static renderers need not. Attach with the current derived data and subsequently update the existing source only when that collection reference changes. Do not change `mapLayers` identity in response to filters: `definitions` is a map-creation effect dependency. Track the last applied collection per renderer, retain the unfiltered response in session state, and distinguish no source records from no selected categories in panel feedback (`Duomenų nėra.` versus `Nepasirinkta atliekų rūšių.`).

**Rationale / alternatives:** Style-layer filters cannot change the membership of an already formed source cluster. Reattaching the source/renderer on every selection would discard events and interaction state; refetching would waste requests. Updating the existing GeoJSON source recalculates clusters and retains camera/basemap state.

### 4. Native bin grouping followed by exact screen-space collision merging

Developer feedback requires that drawn bin markers never overlap, with larger groups at smaller zoom. A larger native radius alone cannot guarantee this: greedy clustering shifts centers, and the displayed radii vary with count. Reuse MapLibre's installed `@maplibre/geojson-vt` clustering engine directly for bin seeds, then apply a screen-space collision pass before rendering. Declare this already installed package as a direct dependency; no additional runtime package is introduced. Landfills retain their existing native source and defaults.

Keep one native bin index and one MapLibre GeoJSON display source. Rebuild the index only on data reference changes or switching between low/high zoom policies: radius 80 below zoom 15, radius 20 at/above 15, clustering through the map's maximum integer zoom (currently 22). Query the buffered viewport from that index; retain complete cached API data. Project seed centers with the actual map camera, check circle radius plus stroke and a small gap, union colliding groups and repeat after each merge until no circles overlap. Repetition is bounded because every merge reduces the number of groups. Preserve native seed references, exact weighted counts and a deterministic Mercator centroid; every member remains resolvable by original bin ID.

Feed only the derived points/groups to a single unclustered display source, with the existing `point_count`-based style layers and delegated click ownership. Native seeds and synthetic aggregates share the same marker radius definition with the collision check. Recompute screen grouping on camera/viewport changes, coalescing work per animation frame and comparing layout signatures to avoid redundant source updates. Keep the existing bin circles/counts visible while MapLibre replaces renderable tiles during camera updates. Source readiness gates interactions, not camera-driven opacity. Only category/data changes temporarily suppress obsolete membership while the latest worker update and tiles load. Filtering remains memoized separately and requests remain lazy/cached.

Below zoom 15, clicking a bin group expands toward its seed expansion zoom, advancing at least one zoom level and clamping to the map maximum. At high zoom it opens the complete member list without moving the view. Count markers use exact counts; high-zoom circles remain compact. Cross-dataset counts are never combined.

**Trade-off:** native index construction and the viewport collision pass run locally. The screen pass is necessary for the explicit non-overlap requirement. Spatial bucketing avoids an all-pairs check; the buffered native query limits work. Developer feedback rejects camera-driven overlay suppression because it makes the selected layer disappear throughout navigation. Use MapLibre's existing tile replacement behavior, retaining loaded markers during asynchronous updates. New cluster geometry is still checked before publication; actual navigation/transition rendering needs browser verification alongside the non-UI geometry check.

### 5. Resolve group items by stable bin identity

At high zoom, retrieve all leaves of each native seed represented by the displayed group, then resolve leaf IDs against the currently applied original-feature index, deduplicate by ID and sort by ascending bin ID. Do not deduplicate by coordinates, inventory number or waste type. Retrieve every represented item; a scrollable bounded list is sufficient for observed groups of up to 21 bins at the same coordinate. No HTTP request or custom backend group endpoint is needed. Native and merged group reads go through the same revision-guarded interaction path.

Build content with safe DOM/text nodes, following the existing landfill presenter and shared `showDetails` popup ownership. List buttons display inventory number (`N/A` for null) and localized waste type. Selecting a button replaces the list content with the existing bin detail presenter and `Atgal į sąrašą`; keep the popup anchored to the group, without panning. Returning restores the same list and appropriate keyboard focus. Ensure long inventory values wrap, the list scrolls within the popup, and Close/Escape keep their existing Lithuanian labels and focus behavior. Inventory, waste type and capacity remain the only data shown; IDs are internal selection keys.

**Rationale / alternatives:** Querying only clicked rendered features can miss members and loses nullable source details. Stable API feature IDs survive filtering and source rebuilding; generating IDs from array positions would select the wrong bin after a filter change. An external drawer would change the existing map-first layout.

### 6. Guard source revisions and asynchronous interaction lifetimes

On a changed data reference, immediately invalidate prior interactions, close the bin popup and refresh the original-feature index, then update the source. Track source revision and await the latest `setData` completion before accepting cluster interactions from that source. Older promises cannot mark a newer update ready. Rapid category changes must leave only the latest membership interactive.

Capture revision plus an interaction sequence on cluster expansion or leaf retrieval. Check that the renderer is still visible, alive, source-current, and the interaction is still the latest before opening a list or moving the camera. Invalidate on source changes, either direction of visibility change, disposal, superseding clicks and map navigation. Navigation after opening a group closes the group's list/detail. Preserve the existing topmost-layer event ownership so a click never opens both landfill and bin content.

A leaf retrieval failure leaves the map and other datasets usable, shows recoverable Lithuanian group feedback (`Nepavyko įkelti konteinerių sąrašo.` with `Bandyti dar kartą`) and does not refetch the bin dataset. If loading feedback is shown in a popup, closing/Escape must also invalidate its pending interaction; extend shared popup close notification minimally if needed. Map recovery attaches fresh renderers using retained category choices and cached/derived data. Remove newly registered navigation and popup callbacks during disposal.

**Rationale / alternatives:** Visibility-only guards do not protect against changed filters, recycled cluster IDs or a delayed response after another click. Reusing the existing revision pattern for data and interaction lifetimes keeps these races local to the renderer.

### 7. Horizontal dataset controls and waste-type modal

Use the existing card with a horizontal flex row of dataset checkboxes, wrapping at narrow widths while retaining its capped scrolling area and the legend outside it. Give every dataset control row the same minimum height as the arrow button and vertically center its checkbox/label, so the arrow does not shift the bin control relative to landfills. Put a small arrow button immediately beside `Konteineriai`, separately from its checkbox. Use the existing shadcn/Radix Dialog primitive with Lithuanian title `Atliekų rūšys`, category checkboxes and `Uždaryti`. The dialog starts closed, changes categories immediately and closes without resetting choices. Radix supplies focus trapping, Escape dismissal and trigger-focus restoration; no inline dropdown/submenu remains. Known controls are available without enabling/loading bins; unknown controls appear only after loaded data establishes their presence. Opening the modal never enables the layer or fetches data.

## Risks / Trade-offs

- [Complete response size and additional high-zoom clustering work] -> Select six columns, reuse feature objects and cached data, and rebuild only on category changes. Verify first enable and category switching against the real approximately 22k-bin snapshot; add no viewport API or optimization dependency without evidence.
- [Pixel grouping differs between integer/fractional zoom and transformed views] -> Project actual marker circles and repeat collision merging to a fixed point; verify integer/fractional zoom, resize, bearing/pitch and maximum zoom. Retain renderable tiles during navigation, gate stale interactions and verify source replacement visually without hiding the layer on camera movement.
- [Filter updates invalidate cluster IDs and pending worker reads] -> Gate interaction on the latest source update and revision/interaction checks; close old popups on filter changes, hiding or navigation.
- [Unexpected types or nullable details] -> Group unknown types under the approved gray Lithuanian fallback and preserve API nulls via original-feature lookup. Verify using temporary browser response overrides, without modifying real records.
- [Accidental map recreation or landfill changes] -> Keep registry identity stable, filter only derived bin data, leave all clustering/list options opt-in and verify both layers enabled together.
- [Running backend connectivity] -> Exploration's HTTP 500 is a verification limitation, not a reason to import or reseed. Use an accessible existing PostgreSQL URL and a backend serving this checkout for acceptance.

## Migration Plan

No schema migration or data preparation is required for the inspected environment. Add the backend endpoint before enabling the frontend definition in a split rollout; normal deployment may deliver both together. Verify directly and through `/api`. Rollback consists of reverting this feature's code and registry entry; stored records and existing APIs are unaffected. Update README and the existing map verification document during implementation, preserving their historical acceptance record.

Validation uses frontend build/lint, strict change validation, a documented repeatable read-only API verification command and a real browser walkthrough. Use temporary response overrides for unknown/null/empty and near-overlap samples; remove overrides before completing acceptance. Automated tests are outside the authorized scope.
