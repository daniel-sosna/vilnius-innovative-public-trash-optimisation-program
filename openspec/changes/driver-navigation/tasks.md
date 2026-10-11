# Tasks

## 1. Fill range 0-4

- [x] 1.1 Add Alembic `0020` replacing `ck_bin_hist_fill_level` with `BETWEEN 0 AND 4`; downgrade raises when a level-4 row exists, else restores `0..3`. Update the `BinHist` check constraint in `models.py`. Verify: `alembic upgrade head` and `downgrade -1` both run on a database with data, and inserting 4 succeeds while 5 is rejected.
- [x] 1.2 In `docs/data-model.md` replace "NULL or 0-3" statements (service history section and the sample-data table row) with 0-4 and the meaning of 4. Verify: `grep -n "0–3\|0-3" docs/data-model.md` returns no fill-level hit.

## 2. Backend route (planning run to driver route)

- [x] 2.1 Record each run's forecast day in the planning run memory and add `demo_driving.latest_routes(forecast_date)` (newest unexpired run of that day). Verify: with a run cached for 2026-09-15, the accessor returns its routes for that day and nothing for another day.
- [x] 2.2 Add `services/driver_route.py`: truck lookup, route from the newest run of the forecast day, stop `path_index` from the legs (landfill returns are not stops), every carrier bin at each stop with inventory number, waste type and site address. Verify: with a cached run, stops carry all carrier bins at the site (not only the due ones) and indexes land on the end of their service legs; inconsistent legs give `navigation_failed`.
- [x] 2.3 Add `interfaces/driver/` router and schemas with `GET /driver/trucks?project_date=` and `POST /driver/route {truck_id, project_date}` (September validation, read-only session, error codes for the screen) and register it in `main.py`. Verify: routed truck → 200 with path and stops; other day or truck without a route → `404 no_plan`; unknown truck → `404 truck_not_found`; missing or out-of-range date → `422`.
- The repeatable `driver.check` command was removed: routes live in the API process's memory, which a separate command cannot read. Checks go through the API.

## 3. Backend service recording

- [x] 3.1 Add `POST /driver/service` taking one stop's list of bins: write session, Pydantic range 0..4 and unique IDs, existing-bin check, one transaction, server Vilnius timestamp expression, `409` on key collision. Verify: with `curl`, a request of three bins (levels 0, 2, 4) stores three rows whose `date` is the server's Vilnius time and ignores a client-supplied date; 5, -1 and a duplicate ID give `422`; one unknown bin gives `404` with no row stored for the others.
- [x] 3.2 Document `docs/driver.md`: route source and lifetime, steps before a Driver run (route calculation on `/admin/routes` for the selected date), simulated parts, load assumption, retry duplicate caveat. Verify: the documented steps lead to a routed truck in the picker.

## 4. Frontend foundations

- [x] 4.1 Add `lib/route-geometry.ts` (cumulative distances, `pointAt`, `bearingAt`, split). Verify: a throwaway script run once with a bent path shows points on the path and bearings within a degree of expected values; remove the script.
- [x] 4.2 Add `pages/driver/api.ts` and `driver-state.ts` (state union, reducer, valid transitions only). Verify: `npm run build` and `npm run lint` pass; a double confirm in `saving_service` is ignored by the reducer.
- [ ] 4.3 Add `/driver` truck picker (trucks routed for the selected day, forecast day shown) and `/driver/:truck_id` routes in `App.tsx` with `ToastProvider`, outside `AdminLayout`, reading the project date; link the role page's `Vairuotojas` button. Verify: at a phone viewport the picker opens from the role page without admin navigation, lists the routed trucks of the selected day or the missing-data message, follows a date change made in the admin calendar, and an unknown truck ID shows the not-found message.

## 5. Navigation screen

- [ ] 5.1 Build `use-route-animator.ts` and `navigation-map.tsx`: route lines (done/remaining), stop states, rotated truck marker, follow camera with padding, smoothed bearing, pan-stops-follow and recenter. Verify: in a browser at 390 px width the truck follows every vertex without cutting corners, is held lower-middle, and recenter works after a pan.
- [ ] 5.2 Build `next-stop-panel.tsx` (next stop address, its bins, progress) and the `Pradėti maršrutą` / `Ruošiamas maršrutas...` / missing / empty / error views in `driver-route-screen.tsx` and `use-driver-workflow.ts`. Verify: each message appears in the right state and navigation is not requested for missing or empty plans.
- [ ] 5.3 Build `bin-level-step.tsx` (inventory number, waste type, `n / N`, five large options that advance on tap, back) and `stop-done-view.tsx` (`Visi konteineriai pažymėti` summary, back, `Patvirtinti`); wire arrival pause, the single batch save, failure toast with retry, resume and completion. Verify: arrival pauses at the exact stop; every carrier bin of the stop is stepped through; tapping advances, back shows the earlier choice and allows changing it; nothing is stored before `Patvirtinti`; 0 and 4 persist to `bin_hist`; a forced failure keeps the all-done view and choices without advancing; the last save shows `Maršrutas baigtas` with the count.

## 6. Verification and docs

- [ ] 6.1 Write `openspec/changes/driver-navigation/verification.md` with the manual flow (prerequisite data, phone viewport, full route, level 0 and 4, save failure, no calculated route, date change, completion) and record the evidence. Verify: every step is run and recorded.
- [x] 6.2 Add the Driver row to the README features table and `docs/driver.md` to the docs index. Verify: README stays under 150 lines and every link resolves.
- [x] 6.3 Run `npm run build`, `npm run lint` and `openspec validate driver-navigation`. Verify: all exit 0.

## Workflow follow-up

- Archive the change after review and manual verification.
