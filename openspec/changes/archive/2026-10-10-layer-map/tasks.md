# Tasks

Completion accepted by the developer on 2026-10-10 after their manual
verification and explicit authorization to complete the checklist and archive.
Browser acceptance is developer-reported. Task 5.2 is closed by that acceptance;
the agent did not independently execute the temporary two-layer browser
experiment. See `docs/map-analytics-verification.md` for the verification record.

## 1. Existing landfill prerequisite

- [x] 1.1 Integrate the accepted main baseline containing the existing `Landfill` model, migrations `0006`/`0007` and catalog API while retaining these planning artifacts; verify those files and contracts are available, resolve any concrete baseline conflict, and add no duplicate landfill model or migration.

## 2. Read-only landfill map API

- [x] 2.1 Add the focused landfill projection service and GeoJSON response schema using the existing model and read-only session; verify field selection, ascending feature IDs, `[longitude, latitude]` order, retained nullable properties and the simple null-coordinate omission through a read-only inspection of the implementation.
- [x] 2.2 Register `GET /map-analytics/landfills` in the existing FastAPI app; verify a successful real API read returns the three seeded Point features and only the specified details, and confirm the existing `/landfills` catalog still serves its prior contract.
- [x] 2.3 Start `docs/map-analytics-verification.md` with repeatable read-only API commands, expected IDs/coordinates from migration `0006`, and explicit success/failure exit behavior; run the documented commands against existing storage without importing, reseeding or changing records.

## 3. Complete clustered landfill slice

- [x] 3.1 Add `/admin/map-analytics` and `Žemėlapio analitika` to the shared layout/navbar; create the large Vilnius-centered analytics canvas using configured map style, existing worker-bundling pattern and resize handling; verify navbar navigation, direct opening, refresh, pan and zoom in the browser.
- [x] 3.2 Add the small layer contract/registry and shared point renderer with namespaced GeoJSON sources, automatic clustering, counts, cluster expansion and feature-detail callbacks; verify the renderer is reusable for point definitions and its lifecycle contract can accommodate a non-point renderer without a marker assumption.
- [x] 3.3 Register `Sąvartynai` with its API loader, appearance and popup presentation and add a labeled `Sluoksniai` checkbox; verify enabling it completes the real backend-to-GeoJSON-to-clustered-map flow and unchecking hides all its style layers.
- [x] 3.4 Add facility-name headings with only operator and address popup rows with known seed descriptions presented in correct Lithuanian and nulls as `N/A`; verify all three individual facilities remain identifiable, cluster clicks expand without detail popups, and hiding the layer closes its popup.
- [x] 3.5 Extend the verification document with the real three-facility zoom/count/popup walkthrough and add README navigation/API/style instructions; verify the walkthrough reproduces zoom-out grouping and zoom-in splitting without modifying the catalog.

## 4. Independent state and responsive controls

- [x] 4.1 Add page-session layer caching, shared pending reads and independent loading/empty/error/retry states, starting with the layer unchecked; verify browser network activity shows no initial landfill read, one first-enable request, no successful-toggle refetch, and no late-response display after unchecking.
- [x] 4.2 Keep the map instance/camera stable across selection changes, clean up resources on unmount, and provide map-specific recovery; verify layer-read failure/retry leaves the basemap usable, rapid toggles preserve center/zoom, and map recovery restores selected cached data.
- [x] 4.3 Complete one card below the full-width map with `Sluoksniai`, name-only checkboxes, then `Legenda` and color meanings; keep long layer lists internally scrollable and suppress pointer-click canvas focus outlines. Verify visible keyboard focus, labeled checkboxes/zoom/popup-close controls, and usable map/popup content at 320px and desktop widths.
- [x] 4.4 Document how to add a point definition or future non-point renderer, and add cache/failure/mobile checks to the verification document; verify the documented extension points match the implemented contract and active IDs resolve to dataset meaning without assistant-specific code.

## 5. Integrated acceptance

- [x] 5.1 Run the frontend build and lint (`npm run build`, `npm run lint` in `frontend/`) and the documented real API/browser walkthrough; verify the two delta specs' observable behavior end to end and existing truck/site navigation and site-detail maps still work. Record results and any actual environment limits in the verification document; add no automated test suite.
- [x] 5.2 Verify simultaneous independent point layers by temporarily registering a second in-memory definition using the same three records through the shared helper, then remove it; confirm separate cluster counts, independent toggles/loading state and layer-specific interaction, and verify the delivered registry/panel contains only `Sąvartynai` with no future layers or database changes.

## 6. Layer colors and compact details refinements

- [x] 6.1 Add renderer-independent color/meaning legend entries to layer definitions, support feature-based point colors and a separate cluster color, and render the extensible Lithuanian legend underneath the map; verify the contract accepts multiple entries and future non-point definitions without shipping future datasets.
- [x] 6.2 Update the documented walkthrough and extension instructions for the shared layer/legend card below the map, name-only labels, pointer focus behavior, green landfill legend and popup heading with only operator/address; run build, lint and OpenSpec validation, and collect the user's browser observations before completing outstanding UI acceptance tasks.
