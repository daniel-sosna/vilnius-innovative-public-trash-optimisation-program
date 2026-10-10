# Proposal

## Why

Žemėlapio analitika currently shows only landfill locations, although the database already contains the city's bin registry. Administrators need to explore those bins by waste type and inspect every bin, including bins whose coordinates overlap even at high zoom.

## What Changes

- Add an independently selectable `Konteineriai` layer, backed by a complete, read-only bin GeoJSON response and the existing MapLibre point-layer helper.
- Place dataset checkboxes horizontally with aligned checkbox/label centers and open waste-type controls in a modal from a small arrow beside `Konteineriai`, with all categories initially selected. Retain category selections when the layer is disabled and re-enabled during the page session; filters update both points and cluster counts without fetching again or recreating the map.
- Color individual bins blue for paper/plastic, green for glass and brown for mixed municipal waste. Unexpected types use gray and the Lithuanian fallback category `Kitos atliekų rūšys`.
- Show inventory number, localized waste type and capacity in lightweight bin popups; null details display `N/A`.
- Keep bins that overlap at high zoom behind a count marker. Clicking that marker opens a selectable bin list, and choosing an item shows that bin's details. Ordinary clusters continue to expand at lower zoom. Use a larger low-zoom grouping radius and merge remaining colliding bin markers until their drawn circles do not overlap. Keep selected bin circles and counts visible during camera movement and cluster updates.
- Change `Sąvartynai` individual markers, their inherited cluster color and the matching legend entry to black, preserving that layer's other behavior and API.
- Keep the existing map-first layout and shared layer/legend card below the map. No bin mutations, additional analytics, new services or map redesign.

## Capabilities

### New Capabilities

None; the existing map capabilities own this extension.

### Modified Capabilities

- `map-analytics`: Add the minimal read-only bin response and Lithuanian bin detail/group interactions.
- `map-layers`: Offer both datasets, add session-preserved waste filtering and category colors, support high-zoom overlap groups for bins, and update the landfill legend/color requirements.

## Impact

- Backend: extend `app/interfaces/map_analytics/{router,schemas}.py` and `app/services/map_analytics.py` with `GET /map-analytics/bins`, selecting only bin ID, coordinates and three detail/filter fields. Use the existing `bins` table and read-only session; no migrations or data imports are needed.
- Frontend: extend the map-analytics API/registry/session/page and add a bin definition/presenter/category mapping. Add small shared renderer/source-update and optional clustering-policy hooks to `components/maps`, keeping landfill defaults intact.
- Dependencies: reuse the installed MapLibre, React and existing UI primitives. Use the already installed MapLibre clustering package directly, with no additional runtime packages, backend pagination, per-bin DOM markers or automated test suite.
- Compatibility: current specs explicitly limit the panel to landfills, require green landfill colors and require unconditional cluster expansion. Delta specs deliberately revise those clauses; the existing landfill/catalog response and popup contract stay intact.
- Confirmed exploration evidence (2026-10-10): a read-only PostgreSQL query found 21,951 bins across the three expected waste-type strings, no missing/invalid coordinates, and 9,814 bins sharing coordinates across 3,705 locations. All required development CSV exports are present. These counts describe the inspected snapshot, not fixed API expectations.
- Assumptions: a new page session resets categories to selected; the fallback checkbox is shown only when unexpected types are present; a neutral cluster color and a scrollable in-popup list keep the UI compact. The high-zoom transition and pixel grouping tolerance are documented design defaults, with an additional screen-space collision merge required by developer feedback. Native radius alone does not guarantee disjoint circles.
- Material verification risks: source updates and asynchronous cluster reads must not expose stale items or move the camera after filtering/hiding. High-zoom grouping needs browser verification at fractional zoom, near-coincident coordinates and maximum zoom. Exploration's running `/sites/stats` endpoint returned HTTP 500 while a direct local PostgreSQL connection succeeded; implementation verification must use a working backend connection and must not count database inspection as UI acceptance.
