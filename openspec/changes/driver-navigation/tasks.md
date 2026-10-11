# Tasks

## 1. Fill range 0-4

- [x] 1.1 Add Alembic `0019` replacing `ck_bin_hist_fill_level` with `BETWEEN 0 AND 4`; downgrade raises when a level-4 row exists, else restores `0..3`. Update the `BinHist` check constraint in `models.py`. Verify: `alembic upgrade head` and `downgrade -1` both run on a database with data, and inserting 4 succeeds while 5 is rejected.
- [x] 1.2 In `docs/data-model.md` replace "NULL or 0-3" statements (service history section and the sample-data table row) with 0-4 and the meaning of 4. Verify: `grep -n "0–3\|0-3" docs/data-model.md` returns no fill-level hit.

## 2. Backend route (stored plans to navigation result)

- [x] 2.1 Produce the static road polyline: export a real-road `LineString` of at least 300 vertices (documented source, licence and method) and commit it as `backend/app/services/data/driver_road_path.geojson`. Verify: the file parses, has finite lon/lat inside Vilnius, and the vertex count is stated in `docs/driver.md`.
- [x] 2.2 Add `services/navigation.py`: `NavigationService` protocol, `MockNavigationService` (even stop placement, last stop at the final vertex) and result validation. Verify: a run with N=1, 6 and 40 stops yields strictly increasing in-range indexes; N larger than the vertex count raises the navigation error.
- [x] 2.3 Add `services/driver_route.py` with `DRIVER_PLAN_DATE`, truck lookup, route-plan trip, collection-plan bins (all of the carrier at each stop) and one `bins` query for `inventory_number` and `waste_type`. Distinguish unknown truck, no plan/trip and empty. Verify: results for a truck with a trip, with none and whose stops are absent from the collection plan.
- [x] 2.4 Add `interfaces/driver/` router and schemas with `POST /driver/route` (read-only collection session, error codes for the screen) and register it in `main.py`. Verify: `curl -X POST /driver/route` returns the contract for a seeded truck, `404` with distinct codes for unknown truck and missing plan, `502` when the mock is forced invalid.
- [x] 2.5 Add a repeatable check `python -m app.interfaces.driver.check --truck-id N` that builds the route and prints stops, bins per stop and path size, exiting 0 when valid and 1 otherwise. Verify: exit codes for a valid truck, an unknown truck and a missing plan.

## 3. Backend service recording

- [x] 3.1 Add `POST /driver/service` taking one stop's list of bins: write session, Pydantic range 0..4 and unique IDs, existing-bin check, one transaction, server Vilnius timestamp expression, `409` on key collision. Verify: with `curl`, a request of three bins (levels 0, 2, 4) stores three rows whose `date` is the server's Vilnius time and ignores a client-supplied date; 5, -1 and a duplicate ID give `422`; one unknown bin gives `404` with no row stored for the others.
- [x] 3.2 Document the endpoints' assumptions in `docs/driver.md` (new file): fixed plan date, prerequisite commands in order (collection plan, demo fleet, route plan), mock parts, retry duplicate caveat. Verify: following the documented commands on a clean database yields a Driver route.

## 4. Frontend foundations

- [x] 4.1 Add `lib/route-geometry.ts` (cumulative distances, `pointAt`, `bearingAt`, split). Verify: a throwaway script run once with a bent path shows points on the path and bearings within a degree of expected values; remove the script.
- [x] 4.2 Add `pages/driver/api.ts` and `driver-state.ts` (state union, reducer, valid transitions only). Verify: `npm run build` and `npm run lint` pass; a double confirm in `saving_service` is ignored by the reducer.
- [ ] 4.3 Add `/driver` truck picker and `/driver/:truck_id` routes in `App.tsx` with `ToastProvider`, outside `AdminLayout`, and link the role page's `Vairuotojas` button. Verify: at a phone viewport the picker opens from the role page without admin navigation and an unknown truck ID shows the not-found message.

## 5. Navigation screen

- [ ] 5.1 Build `use-route-animator.ts` and `navigation-map.tsx`: route lines (done/remaining), stop states, rotated truck marker, follow camera with padding, smoothed bearing, pan-stops-follow and recenter. Verify: in a browser at 390 px width the truck follows every vertex without cutting corners, is held lower-middle, and recenter works after a pan.
- [ ] 5.2 Build `next-stop-panel.tsx` (next stop address, its bins, progress) and the `Pradėti maršrutą` / `Ruošiamas maršrutas...` / missing / empty / error views in `driver-route-screen.tsx` and `use-driver-workflow.ts`. Verify: each message appears in the right state and navigation is not requested for missing or empty plans.
- [ ] 5.3 Build `bin-level-step.tsx` (inventory number, waste type, `n / N`, five large options that advance on tap, back) and `stop-done-view.tsx` (`Visi konteineriai pažymėti` summary, back, `Patvirtinti`); wire arrival pause, the single batch save, failure toast with retry, resume and completion. Verify: arrival pauses at the exact stop; every carrier bin of the stop is stepped through; tapping advances, back shows the earlier choice and allows changing it; nothing is stored before `Patvirtinti`; 0 and 4 persist to `bin_hist`; a forced failure keeps the all-done view and choices without advancing; the last save shows `Maršrutas baigtas` with the count.

## 6. Verification and docs

- [ ] 6.1 Write `openspec/changes/driver-navigation/verification.md` with the manual flow (prerequisite data, phone viewport, full route, level 0 and 4, save failure, missing and empty plan, mock-invalid navigation, completion) and record the evidence. Verify: every step is run and recorded.
- [x] 6.2 Add the Driver row to the README features table and `docs/driver.md` to the docs index. Verify: README stays under 150 lines and every link resolves.
- [x] 6.3 Run `npm run build`, `npm run lint` and `openspec validate driver-navigation`. Verify: all exit 0.

## Workflow follow-up

- Archive the change after review and manual verification.
