# Design

## Context

See `proposal.md` for motivation and `specs/driver-navigation/spec.md` for behaviour.

Observed state after merging `main`:

- The route planning screen (`/admin/routes`, `demo-planning`) predicts the forecast day, solves each carrier with PyVRP and resolves every truck's trips through OSRM. `demo_navigation.navigate` returns a `NavigationResponse` with a `run_id`; `demo_driving.remember_routes` keeps the newest three runs for one hour in the worker's memory, by run and truck. A route has the full road `path`, service `stops` (`site_id`, due `bin_ids`) and `legs` that partition the path, each tagged with its service-stop index or `None` for a landfill return.
- Stored route plans (`route_plans`) still exist but have straight-line estimates only, no road geometry.
- The project date (`project-date`) is an app-root React context persisted in localStorage; the forecast day is T+1.
- `bin_hist` has `CHECK (fill_level BETWEEN 0 AND 3)` (migration 0004) and a unique key `(bin_id, date, was_serviced)`. `resident_requests` already stamps `statement_timestamp() AT TIME ZONE 'Europe/Vilnius'` on the server.
- Writable endpoints use short transactions (`collection_write_session.py`). The frontend calls `/api/...` through page-local `api.ts` modules. `ToastProvider` exists.

## Goals / Non-Goals

**Goals:** a complete, demonstrable Driver vertical slice from the calculated routes to saved observations; reuse of the planning screen's routes without recalculating them; a driver screen split into small units.

**Non-Goals:** real GPS, persisting calculated routes, recalculating routes for the Driver, authentication, route history or persistence of progress, offline use, spoken instructions, changing prediction or route calculation.

## Decisions

### 1. Route source: the planning run memory

The run memory also records each run's forecast day. `demo_driving.latest_routes(forecast_date)` returns the routes of the newest unexpired run of that day. `GET /driver/trucks?project_date=` lists its trucks; `POST /driver/route {truck_id, project_date}` returns one truck's route. A missing run or a truck without a route → `404 no_plan`; an unknown truck → `404 truck_not_found`.

Alternatives: stored route plans (rejected: no road geometry, and the planning screen no longer stores plans); recalculating for the Driver (rejected: minutes of prediction and solving, and could differ from what the administrator saw); persisting runs in the database (rejected for now: new schema for a transient demo result). The consequence is that routes vanish after an hour or a backend restart, which is documented.

Stops keep the run's driving order. Each stop is expanded to every bin of the truck's carrier at the site (one `bins` query), because the truck empties them all; the run's due `bin_ids` must be among them, else `409 bin_missing`. Addresses come from `sites`.

### 2. Stop positions from the legs

Legs share their boundary vertex, so a service leg ends at path vertex `sum(len(leg.path) - 1)` over the legs up to it. That vertex is the stop's `path_index`. Landfill-return legs advance the index without creating a stop. If the summed legs do not reach the end of the path, or a service stop has no leg, the route is rejected with `502 navigation_failed`. Two stops snapped to the same vertex give equal indexes, so positions are non-decreasing rather than strictly increasing. The route ends at the last service stop; the return to the landfill stays visible as road ahead.

### 3. Response contract

```text
GET /driver/trucks?project_date=T -> [{truck_id, truck_name, stop_count, bin_count}]
POST /driver/route {truck_id, project_date} -> {
  truck_id, plan_date,
  path: [{latitude, longitude}],
  stops: [{ site_id, address, path_index,
            bins: [{bin_id, inventory_number, waste_type}] }]
}
```

`plan_date` is the forecast day. Bin order inside a stop is by bin ID. The screen keeps latitude/longitude only inside `path`.

### 4. Recording a service

`POST /driver/service {services: [{bin_id, fill_level}]}` takes one stop's bins. It uses the write session, validates a non-empty list of unique bin IDs with levels `0..4` with Pydantic (`422`), checks every bin exists (`404`), and inserts one `BinHist` row per bin in a single transaction, each with `was_serviced=true`, `fill_level`, and `date = timezone('Europe/Vilnius', statement_timestamp())` as a SQL expression, with no schema default and no client value. The transaction commits or rolls back as a whole, so a stop is never half saved. It returns the stored rows' `id` and `date`. A unique-key collision returns `409`. Other database errors return `500`.

Idempotency is not attempted. The screen prevents double submission by state (decision 7); a retry after a network failure whose first request succeeded may store a second row. This is accepted for the MVP and noted in the docs.

### 5. Fill-range migration

Alembic `0020` drops `ck_bin_hist_fill_level` and adds it back as `fill_level BETWEEN 0 AND 4`. Data are untouched. Downgrade raises if any row has level 4, then restores `0..3`. The model's `CheckConstraint` and `docs/data-model.md` change with it. The `collection-records` delta covers the behaviour.

### 6. Shared geometry helper

`frontend/src/lib/route-geometry.ts` holds pure functions over `[lon, lat]` arrays: cumulative distances (equirectangular, as the map needs approximate metres), `pointAt(distance)`, `bearingAt(distance, lookahead)`, and `split(distance)` for done/remaining lines. It has one consumer now, but is kept pure and separate so a later admin or demo screen can reuse it.

### 7. Frontend structure and state

Under `frontend/src/pages/driver/`:

| Unit | Responsibility |
|---|---|
| `api.ts` | `loadTruckRoutes`, `loadRoute`, `saveService`, typed errors, route validation |
| `driver-state.ts` | reducer and state union |
| `use-driver-workflow.ts` | wires reducer, API calls, animator |
| `use-route-animator.ts` | requestAnimationFrame loop that advances a distance along the path while state is `navigating` |
| `navigation-map.tsx` | MapLibre map, route lines, stop layer, truck marker, camera |
| `next-stop-panel.tsx` | next bin, progress, completion text |
| `bin-level-step.tsx` | one bin: identifier, `n / N`, five options, back |
| `stop-done-view.tsx` | all-done summary, back, `Patvirtinti`, error toast hook |
| `driver-route-screen.tsx` | composes the above for `/driver/:truck_id` |
| `truck-picker-page.tsx` | `/driver` list of the trucks routed for the selected day |

State is one discriminated union: `idle`, `preparing_route`, `navigating {distance}`, `at_bin {stopIndex, step, levels}` (`step` is the bin index, or the bin count for the all-done view), `saving_service {stopIndex, levels}`, `completed {serviced}`, `error {reason, retry}`. The reducer allows only valid transitions. `saving_service` ignores further confirm actions. Save failure returns to `at_bin` with all selections kept; the toast uses the existing provider. Serviced stops are tracked by index; progress counts the bins of serviced stops, so there is no second source of truth.

A stop is stepped through bin by bin. Tapping a level stores it in `levels` and increments `step`; back decrements it (bounded at 0, so the first bin has no back that leaves the stop) and shows the stored choice. At `step == bin count` the all-done view shows the summary; only its `Patvirtinti` leaves `at_bin`, sending all levels in one request, so a mistaken tap can be corrected before anything is stored. Tapping advances immediately (no per-bin confirm), which keeps a stop to one tap per bin.

Alternative: save each bin on tap. Rejected: it allows half-saved stops and removes the chance to correct the last answer.

The animator moves at a constant demo speed (a named constant, scaled for a visible demo; not a claim about real speed). Arrival is detected when the travelled distance reaches the next unserviced stop's cumulative path distance; the animator stops exactly there. Resume continues from that distance. It uses `performance.now()` deltas and caps a single step so a background tab resuming does not teleport the truck past stops.

### 8. Map and camera

A direct MapLibre map as in `route-map.tsx`, not `AnalyticsMap`, because navigation needs bearing, padding and per-frame updates the analytics lifecycle does not offer. One GeoJSON source holds the done and remaining line; a second holds stops with a `state` property (`done`, `next`, `future`) driving circle styling. The truck is a single `Marker` rotated to the bearing.

Per frame the camera uses `jumpTo` with the truck as centre, a fixed zoom, a top padding of about half of the map height (truck in the lower-middle), and a bearing smoothed toward the bearing of a point a short distance ahead (fixed lookahead and low-pass factor, with a step cap) to avoid jitter at vertices. A `dragstart` caused by user input sets `following=false`; the recenter button sets it back. The map is not recreated between states.

### 9. Routing and chrome

`/driver` and `/driver/:truck_id` are siblings of `/admin` in `App.tsx`, wrapped in `ToastProvider` and inside the app-root `ProjectDateProvider`. The Driver only reads the project date (`useProjectDate`); the calendar stays in the admin layout. The screen keys its workflow by the date, so a date change restarts it from idle. The screen fills `100dvh` with the map and overlays the panels at the top and bottom, with controls of at least 48 px. The role page's `Vairuotojas` button links to `/driver`.

## Risks / Trade-offs

- [No calculated route: never run, expired after an hour, evicted by newer runs, or lost on backend restart] → missing-data state in picker and screen; `docs/driver.md` says to run the calculation on `/admin/routes` for the selected date first.
- [Several backend workers would each hold their own runs] → one worker, as the planning screen already requires.
- [Loads were sized for due bins only, while the driver records every carrier bin] → documented assumption; capacities can be exceeded on paper.
- [Route geometry inconsistent with its stops] → rejected with a route error rather than shown with wrong stop positions.
- [Accidental tap advances to the next bin] → back returns with the choice shown, and the all-done summary allows review before saving.
- [Retry after a lost response can store a duplicate row] → accepted for the MVP, documented; the unique key limits identical-instant duplicates only.
- [Camera jitter at sharp vertices] → look-ahead bearing, smoothing and step cap; check manually on a real phone width.
- [Changing the check constraint scans `bin_hist`] → one short migration on a hackathon-size table; downgrade refuses when level 4 rows exist.
- [requestAnimationFrame throttled in a background tab] → capped step per frame.

## Migration Plan

1. Deploy migration `0020` (additive widening; existing rows stay valid).
2. Deploy the backend with the new router, then the frontend.
3. Roll back by removing the routes; downgrade `0020` only if no level 4 rows exist.
