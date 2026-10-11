# Design

## Context

See `proposal.md` for motivation and `specs/driver-navigation/spec.md` for behaviour.

Observed state of this branch:

- The stored route plan (`route_plans` → trucks → trips → stops) is read by `route_plan.get_stored_plan(session, date, carrier)`. A stop has `site_id`, coordinates and `bin_count` but no bin IDs.
- `collection_plan.get_plan(session, date, [carrier])` returns the carrier's stops by `site_id`, each with its bins (`bin_id`, `waste_type`, `due`). It lists every carrier bin at the site with a `due` flag, skips stops without a due bin, and does not return `inventory_number`.
- `bin_hist` has `CHECK (fill_level BETWEEN 0 AND 3)` (migration 0004) and a unique key `(bin_id, date, was_serviced)`. `resident_requests` already stamps `statement_timestamp() AT TIME ZONE 'Europe/Vilnius'` on the server.
- Writable endpoints use short transactions (`collection_write_session.py`). The frontend calls `/api/...` through page-local `api.ts` modules; `route-map.tsx` shows the project's direct MapLibre setup (`setWorkerUrl`, `VITE_MAP_STYLE_URL`). `ToastProvider` exists.
- No Navigation Service, global project date or truck animation exists on this branch.

## Goals / Non-Goals

**Goals:** a complete, demonstrable Driver vertical slice from stored plans to saved observations; a navigation interface the real router can replace without touching the screen; a driver screen split into small units.

**Non-Goals:** real GPS, real routing (OSRM/Valhalla/OR-Tools), a date selector, authentication, route history or persistence of progress, offline use, spoken instructions, multiple trips, changing prediction, collection-plan or route-plan code, an admin demo screen.

## Decisions

### 1. Source of stops: route plan order + collection plan bins

`POST /driver/route {truck_id}` loads the truck, then the route plan of its carrier for `DRIVER_PLAN_DATE` and finds the truck's first trip. The collection plan of the same date and carrier gives all the carrier's bins per `site_id` (the truck empties them all, per the collection-plan spec; `due` is not used by the Driver); `inventory_number` and `waste_type` come from one `bins` query by ID. A trip stop absent from the collection plan is dropped.

Alternative: the collection plan alone. Rejected: it has no per-truck split or order, so every driver would see the same list.

`DRIVER_PLAN_DATE` is one constant in `services/driver_route.py`, documented as a placeholder for the later date selector. The frontend never holds the date.

The endpoint reads only the database through a read-only collection session. Missing route plan, missing truck in the plan, or no trip → `404` with a code the screen maps to the missing-data message. A trip none of whose stops is in the collection plan → `200` with an empty `stops` list, which the screen maps to the empty message. Unknown truck → `404` with a different code.

### 2. Navigation service: interface plus a static mock

`services/navigation.py` defines a `NavigationService` protocol: `build(stops: list[StopIn]) -> NavigationResult` where the result is `path: list[(lat, lon)]` and `stop_index: list[int]` (path vertex of each stop). `MockNavigationService` loads a static GeoJSON `LineString` from `backend/app/services/data/driver_road_path.geojson`, and places N stops at evenly spaced vertices, the last at the final vertex. A validation function checks at least 2 finite points, indexes strictly increasing and within range; failure raises an error mapped to `502` with a navigation-error code.

The mock deliberately ignores the stops' real coordinates. This is stated in the docs and the proposal; it is the price of a fixed, offline, network-free path. If N exceeds the path's vertex count the mock raises the same navigation error.

The router depends on the protocol through one module-level factory so the real implementation is a one-line swap.

Alternative: call public OSRM at runtime. Rejected: network failure modes, rate limits, and the brief puts routing out of scope.

**Path data:** the polyline is generated once by the developer from real roads (e.g. a one-off OSRM or OSM export for a stretch of Vilnius streets), committed as data with its source and licence noted in `docs/driver.md`, and never fetched at runtime. It needs a few hundred vertices so movement is visibly road-following and enough vertices exist for the largest trip. `docs/driver.md` states the size limit.

### 3. Response contract

```text
POST /driver/route -> {
  truck_id, plan_date,
  path: [{latitude, longitude}],
  stops: [{ site_id, address, path_index,
            bins: [{bin_id, inventory_number, waste_type}] }]
}
```

Bin order inside a stop is by bin ID. The screen keeps latitude/longitude only inside `path`, so the contract can change behind the navigation service.

### 4. Recording a service

`POST /driver/service {services: [{bin_id, fill_level}]}` takes one stop's bins. It uses the write session, validates a non-empty list of unique bin IDs with levels `0..4` with Pydantic (`422`), checks every bin exists (`404`), and inserts one `BinHist` row per bin in a single transaction, each with `was_serviced=true`, `fill_level`, and `date = timezone('Europe/Vilnius', statement_timestamp())` as a SQL expression, with no schema default and no client value. The transaction commits or rolls back as a whole, so a stop is never half saved. It returns the stored rows' `id` and `date`. A unique-key collision returns `409`. Other database errors return `500`.

Idempotency is not attempted. The screen prevents double submission by state (decision 7); a retry after a network failure whose first request succeeded may store a second row. This is accepted for the MVP and noted in the docs.

### 5. Fill-range migration

Alembic `0019` drops `ck_bin_hist_fill_level` and adds it back as `fill_level BETWEEN 0 AND 4`. Data are untouched. Downgrade raises if any row has level 4, then restores `0..3`. The model's `CheckConstraint` and `docs/data-model.md` change with it. The `collection-records` delta covers the behaviour.

### 6. Shared geometry helper

`frontend/src/lib/route-geometry.ts` holds pure functions over `[lon, lat]` arrays: cumulative distances (equirectangular, as the map needs approximate metres), `pointAt(distance)`, `bearingAt(distance, lookahead)`, and `split(distance)` for done/remaining lines. It has one consumer now, but is kept pure and separate so a later admin or demo screen can reuse it.

### 7. Frontend structure and state

Under `frontend/src/pages/driver/`:

| Unit | Responsibility |
|---|---|
| `api.ts` | `loadRoute`, `saveService`, typed errors |
| `driver-state.ts` | reducer and state union |
| `use-driver-workflow.ts` | wires reducer, API calls, animator |
| `use-route-animator.ts` | requestAnimationFrame loop that advances a distance along the path while state is `navigating` |
| `navigation-map.tsx` | MapLibre map, route lines, stop layer, truck marker, camera |
| `next-stop-panel.tsx` | next bin, progress, completion text |
| `bin-level-step.tsx` | one bin: identifier, `n / N`, five options, back |
| `stop-done-view.tsx` | all-done summary, back, `Patvirtinti`, error toast hook |
| `driver-route-screen.tsx` | composes the above for `/driver/:truck_id` |
| `truck-picker-page.tsx` | `/driver` list of trucks |

State is one discriminated union: `idle`, `preparing_route`, `navigating {distance}`, `at_bin {stopIndex, step, levels}` (`step` is the bin index, or the bin count for the all-done view), `saving_service {stopIndex, levels}`, `completed {serviced}`, `error {reason, retry}`. The reducer allows only valid transitions. `saving_service` ignores further confirm actions. Save failure returns to `at_bin` with all selections kept; the toast uses the existing provider. Serviced stops are tracked by index; progress counts the bins of serviced stops, so there is no second source of truth.

A stop is stepped through bin by bin. Tapping a level stores it in `levels` and increments `step`; back decrements it (bounded at 0, so the first bin has no back that leaves the stop) and shows the stored choice. At `step == bin count` the all-done view shows the summary; only its `Patvirtinti` leaves `at_bin`, sending all levels in one request, so a mistaken tap can be corrected before anything is stored. Tapping advances immediately (no per-bin confirm), which keeps a stop to one tap per bin.

Alternative: save each bin on tap. Rejected: it allows half-saved stops and removes the chance to correct the last answer.

The animator moves at a constant demo speed (a named constant, scaled for a visible demo; not a claim about real speed). Arrival is detected when the travelled distance reaches the next unserviced stop's cumulative path distance; the animator stops exactly there. Resume continues from that distance. It uses `performance.now()` deltas and caps a single step so a background tab resuming does not teleport the truck past stops.

### 8. Map and camera

A direct MapLibre map as in `route-map.tsx`, not `AnalyticsMap`, because navigation needs bearing, padding and per-frame updates the analytics lifecycle does not offer. One GeoJSON source holds the done and remaining line; a second holds stops with a `state` property (`done`, `next`, `future`) driving circle styling. The truck is a single `Marker` rotated to the bearing.

Per frame the camera uses `jumpTo` with the truck as centre, a fixed zoom, a top padding of about half of the map height (truck in the lower-middle), and a bearing smoothed toward the bearing of a point a short distance ahead (fixed lookahead and low-pass factor, with a step cap) to avoid jitter at vertices. A `dragstart` caused by user input sets `following=false`; the recenter button sets it back. The map is not recreated between states.

### 9. Routing and chrome

`/driver` and `/driver/:truck_id` are siblings of `/admin` in `App.tsx`, wrapped in `ToastProvider`. The screen fills `100dvh` with the map and overlays the panels at the top and bottom, with controls of at least 48 px. The role page's disabled button becomes a link to `/driver`.

## Risks / Trade-offs

- [Prerequisite data missing: plans, demo fleet, a truck with a trip] → clear missing-data state; `docs/driver.md` lists the commands in order; verification starts with them.
- [Static path is fixed and short] → vertex-count check fails loudly; the data file needs a documented minimum size.
- [Stops on the map are not the real bin positions] → disclosed in docs and spec; bins and order remain real.
- [Collection plan rebuilt after the route plan] → stops absent from the collection plan are dropped, and the route simply gets shorter.
- [Accidental tap advances to the next bin] → back returns with the choice shown, and the all-done summary allows review before saving.
- [Retry after a lost response can store a duplicate row] → accepted for the MVP, documented; the unique key limits identical-instant duplicates only.
- [Camera jitter at sharp vertices] → look-ahead bearing, smoothing and step cap; check manually on a real phone width.
- [Changing the check constraint scans `bin_hist`] → one short migration on a hackathon-size table; downgrade refuses when level 4 rows exist.
- [requestAnimationFrame throttled in a background tab] → capped step per frame.

## Migration Plan

1. Deploy migration `0019` (additive widening; existing rows stay valid).
2. Deploy backend with the new router and data file, then the frontend.
3. Roll back by removing the routes; downgrade `0019` only if no level 4 rows exist.

## Open Questions

- Which stretch of Vilnius roads provides the static path, and how many vertices are needed for the largest demo trip? To be settled when the data file is produced (task 2.1); it changes no spec.
