# Proposal

## Why

Administrators can inspect individual collection-site locations, but cannot explore multiple datasets together on a large map. A map analytics screen with the existing landfill catalog provides a complete first slice and a practical foundation for later VipTop analytical layers.

## What Changes

- Add `Žemėlapio analitika` to the shared admin navbar and serve `/admin/map-analytics`, including direct navigation and refresh.
- Show a large interactive MapLibre map centered on Vilnius using the existing `VITE_MAP_STYLE_URL` setting, with one compact responsive card underneath containing `Sluoksniai`, its labeled checkboxes, then `Legenda` and its color meanings. Omit descriptive text from layer labels and suppress the map outline on pointer clicks while preserving keyboard focus.
- Introduce a small layer registry separating dataset identity, meaning, loading, rendering, visibility and interaction from the map component. Allow multiple active layers and extension to non-point renderers without implementing future layers.
- Make clustering a shared, automatic capability of point layers: zoom-dependent clusters, counts, cluster expansion and clickable individual features using MapLibre GeoJSON sources and style layers.
- Add the sole initial layer, `Sąvartynai`, loading real records from the existing `Landfill` model through a focused read-only GeoJSON endpoint. Show the facility name as the heading and operator/address as the only detail rows in a lightweight popup.
- Load a layer on first enable, retain its data for the page session, and hide/show it without rebuilding the map. Proposed initial state: all layers unchecked.
- Define layer colors and an extensible `Legenda` section in the shared card beneath the map, initially green for `Sąvartynai`. Allow multiple legend entries and feature-based point colors for later categories without implementing future datasets.
- Use correct Lithuanian throughout the interface and known seed-value presentation, with `N/A` for displayed nulls. If either coordinate is null, simply omit that marker.

Out of scope: bins/sites layers, polygon analytics, grids, heatmaps, routes, driver navigation, analytics assistants or chat, landfill management and database redesign.

## Capabilities

### New Capabilities

- `map-analytics`: Admin map navigation, map-first screen, configurable basemap and read-only landfill presentation/API.
- `map-layers`: Selectable independent datasets, reusable point clustering and interactions, and an extension contract for future layer types.

### Modified Capabilities

None. Existing site browsing, landfill catalog reads and truck assignment behavior retain their current contracts.

## Impact

- Frontend: admin routes/navbar, a new map analytics page, layer definitions and shared map-layer helpers. Reuse React, TypeScript, MapLibre and existing UI primitives; no new GIS framework or service.
- Backend: new `/map-analytics/landfills` read endpoint, response schema and projection service; register it in the existing FastAPI app. Browser requests follow the existing same-origin `/api` proxy convention.
- Database: use existing landfill storage and coordinates without new migrations, imports or reseeding. The user confirmed that the live catalog contains the three entries defined by the seed migration.
- Implementation prerequisite: this `layer-map` checkout predates the landfill work. The locally available `origin/main` reference (`db3ce5f` at proposal time) contains `Landfill`, migrations `0006`/`0007`, and `GET /landfills`. Build on that accepted baseline rather than recreating those changes.
- Material limits: live database inspection was unavailable because Docker access was denied. Seed coordinates include approximate address locations; displaying them does not establish surveyed entrances, operating status or routing suitability. External map-resource availability remains dependent on the configured provider.
- Verification: frontend build/lint, repeatable read-only API checks and manual browser checks against the three real records. No automated test suite is added.
