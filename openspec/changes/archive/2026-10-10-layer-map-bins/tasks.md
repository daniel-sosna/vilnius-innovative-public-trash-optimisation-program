# Tasks

## 1. Read-only bin map API

- [x] 1.1 Add bin GeoJSON response schemas, the six-column ordered projection and `GET /map-analytics/bins` using `CollectionSession`; verify a read against the existing database returns each displayable bin once, sorted by ID, with `[longitude, latitude]`, exactly three properties, numeric/null capacity and no pagination or unrelated fields.
- [x] 1.2 Extend `docs/map-analytics-verification.md` with a repeatable read-only bin API command accepting a backend URL; run it directly and through `/api`, compare count/type totals with a read-only database query, and inspect null/empty/unusable-coordinate handling without modifying records. Record useful output and a nonzero failure exit. Check the required CSV files before using collection data; do not run `bin_sync`.
- [x] 1.3 Document the bin response contract in README's map analytics section; verify the documented URL/fields match the live endpoint and that the existing landfill/catalog API verification still passes unchanged.

## 2. Bin layer, colors and individual details

- [x] 2.1 Add the abortable bin API loader/type and one local category mapping for the three exact observed source values plus the gray `Kitos atliekų rūšys` fallback; verify the frontend build accepts the response type and that generated marker expressions, labels and legend entries use the same category definitions.
- [x] 2.2 Add the `bins` point definition, safe DOM detail presenter and registry entry; verify in the browser that first enable renders database bins through the shared GeoJSON/style layers, marker colors match waste types, and individual popups show only inventory number, localized waste type and capacity. Use temporary response overrides to check nulls and unknown types without storage changes.
- [x] 2.3 Change the existing landfill color constant to black and preserve its inherited cluster color/legend; verify black individual markers, clusters and swatch while cluster expansion, facility popup fields and landfill API remain as before.
- [x] 2.4 Update README and the map verification walkthrough for both independently selectable layers, category colors, individual-bin details and black landfills; perform the documented first-enable/color/popup steps against the running app and record actual outcomes.

## 3. Category filtering with session reuse

- [x] 3.1 Add the optional renderer data-update contract and rendered-data synchronization path; implement point-source updates with current original-feature lookup, reference guards and latest-update readiness. Verify a data change rebuilds that source's clusters without a new map/source attachment, stale feature details or camera movement, and verify the static landfill renderer still works.
- [x] 3.2 Add page-lifetime bin category state and memoized filtered FeatureCollections, retaining the unfiltered session cache; verify toggling the main layer preserves category choices including all-deselected state, and zooming/main toggles do not rerun filtering or request data.
- [x] 3.3 Add horizontal wrapping dataset controls and a small arrow opening an accessible waste-type modal with category checkboxes, conditionally showing the initially selected fallback category; verify opening/closing the modal does not toggle the layer, all categories start selected, independent choices immediately affect counts/points, and no-selected-category feedback differs from empty/error data states.
- [x] 3.4 Extend the filter walkthrough in the existing verification document; perform subset, all-off, off/on restoration, new-page reset and map-recovery checks. Use browser Network tools to verify no initial dataset requests, one shared first-enable read and no filter/toggle/zoom reads; confirm camera and the other layer remain unchanged.

## 4. High-zoom overlap groups and bin selection

- [x] 4.1 Add opt-in clustering configuration and high-zoom group interaction hooks to the point helper; configure native bin seeds with the documented low/high zoom radii and iterative screen-space collision merging through maximum map zoom, while keeping landfill defaults. Verify ordinary bin clusters expand below zoom 15, near bins separate when zoom permits, and identical-coordinate bins retain one exact-count marker through maximum zoom; check fractional zoom and supported source/map limits.
- [x] 4.2 Add high-zoom native/merged group-leaf retrieval and the compact scrollable group presenter, resolving every member through stable IDs and original properties; verify a group of two bins and a real larger colocated group list every member once, each button opens the correct three-field detail, and `Atgal į sąrašą` permits selecting another bin without camera movement or an HTTP request.
- [x] 4.3 Guard source revisions, pending cluster reads, superseding clicks, visibility changes and disposal; close group popups on navigation, invalidate pending work when applicable, and add recoverable Lithuanian group-read feedback. Verify rapid filters, hide/show, zoom/pan, Close/Escape during loading and navigation away cannot reopen stale content or move the camera; group retry must not reload the dataset.
- [x] 4.4 Document and perform the overlap walkthrough using real coincident bins plus temporary near-coordinate, duplicate/null inventory and unexpected-type response overrides; verify same-type bins stay individually reachable, list counts exclude filtered categories, a group reduced to one bin becomes an individual marker, and list scrolling/keyboard focus work. Remove overrides before accepting the results.

## 5. Integration acceptance

- [x] 5.1 Verify both real datasets enabled together maintain independent source counts, visibility, failures, retry and topmost-click ownership; repeat dataset loading races and successful-empty response overrides, and confirm the basemap remains usable when one dataset fails.
- [x] 5.2 Complete desktop and 320-pixel browser acceptance: horizontal dataset controls, accessible scrolling modal, internally scrolling layer list, reachable legend, group/detail popup wrapping/scrolling, Lithuanian controls, keyboard focus and existing navigation/site-map regressions. Record observations in the verification document without marking unobserved UI behavior complete.
- [x] 5.3 Run `npm run build` and `npm run lint` from `frontend/`, `git diff --check` and `openspec validate layer-map-bins --strict`; rerun the documented read-only bin and landfill API commands against the final running checkout and ensure temporary overrides or development-only definitions are absent.

## 6. Developer-requested visual fixes

- [x] 6.1 Implement native seed grouping with an iterative spatial collision merge for bins; provide and run a repeatable read-only layout verification command against the real registry at low, fractional and maximum zoom, checking disjoint marker circles, exact counts, complete unique membership and near/identical-coordinate cases. Record timing and preserve landfill clustering.
- [x] 6.2 Verify aligned horizontal dataset checkboxes and the arrow-triggered waste-type modal in the running browser, including independent visibility, keyboard/Escape focus restoration, category persistence and 320-pixel layout; verify bin circles/counts remain visible throughout pan/zoom/rotate/resize and source replacement, with correct settled groups. Record actual observations without accepting unobserved UI behavior.
- [x] 6.3 Equalize dataset control row heights and retain bin circle/count opacity during camera-driven layout updates and re-enabling. Preserve latest-source interaction guards and suppression of excluded members on filter changes; inspect MapLibre's tile replacement behavior and run build/lint checks. Document browser-only transition verification separately.
