# Verification evidence

## Fleet and collection plan (tasks 1.2, 1.3)

Collection plan built with `python -m app.interfaces.collection_plan --date 2026-09-15` (plan date 2026-09-16, threshold 2): 8,863 due bins; stops Ecoservice 2,613, Ekonovus 2,305, Kauno švara 1,288.

`python -m app.interfaces.demo_fleet --date 2026-09-16` (capacities 10/16/20 m3, shift 480 min, assumed trip 90 min, seed 0):

| Carrier | Stops | Load (m3) | Trucks |
|---|---|---|---|
| Ecoservice | 2,613 | 6,886 | 102 |
| Ekonovus | 2,305 | 6,434 | 95 |
| Kauno švara | 1,288 | 1,999 | 30 |

- Second run: same 227 demo trucks (identical checksum of name/capacity/landfill), no duplicates.
- A hand-entered truck ("Hand truck", Ecoservice) was untouched by both runs.
- A date without a collection plan exits 1 with "the collection plan must be built first".
- Stop loads are skewed: Ecoservice median 0.58 m3, p90 about 10 m3, max 28.8 m3. Ten Ecoservice stops exceed the largest truck (20 m3).

## Solver spike (task 1.4)

PyVRP 0.14.0 with numpy 1.26.4 (both in the backend venv).

Hand-checked instance (1 landfill, 1 truck of 10 m3, 4 stops of 4 m3 on a line at 1, 2, 3, 4 km, shift 2 h, unloading 15 min, service 5 min):
- Expected: two trips of two stops, 4 + 8 = 12 km. Got: 12,000 m, 2 trips, reload at the landfill between them.
- Duration 39,000 s = 36,000 driving + 1,200 service + 1,800 depot service. Overtime 31,800 s = 39,000 - 7,200. Cost 5,322,600 = 12,000 (distance) + 31,800 x 167 (overtime), as designed.
- Finding: `Depot.service_duration` is charged at the start and at every reload, not at the end of the last trip. Unloading is therefore modelled as extra duration on every edge that arrives at a landfill, with depot service 0 (design D3 updated).
- Finding: matrices are built with numpy (`ProblemData`); adding millions of edges one by one is not an option.

Full instance (Ecoservice, 2,603 stops after removing 10 oversize, 103 trucks, 6,647 m3, haversine x 1.3, 30 km/h, 5 min service, 15 min unloading, 8 h shift, 3 landfills):

| Iterations | Time | km | Trips | Trucks used | Overtime |
|---|---|---|---|---|---|
| 100 | 8 s | 12,056 | 437 | 103 | 0 |
| 1,500 | 89 s | 11,835 | 436 | 103 | 0 |

A 300-stop, 15-truck slice solves in 1.2 s (300 iterations). The matrix is about 2,600 x 2,600 and fits in memory.

## Overtime penalty sweep (task 1.5)

Undersized fleet to force overtime: first 60 Ecoservice trucks (950 m3 per round) against 6,647 m3, 600 iterations each.

| Penalty (km per overtime minute) | km | Trips | Overtime (min) |
|---|---|---|---|
| 1 | 11,275 | 421 | 13,081 |
| 3 | 11,297 | 426 | 13,197 |
| 10 | 11,328 | 425 | 13,245 |
| 30 | 11,346 | 428 | 13,327 |

The curve is flat: a 30x change in penalty moves km by 0.6% and overtime by 1.9%, because with every truck over its shift the total overtime is set by the workload. The default stays at 10. Default effort limit: 1,000 iterations (about 60 s for the largest carrier), fixed seed.

Note: with the 102-truck demo fleet there is no overtime at all, so the demo fleet is not undersized; a busier demo uses a larger `--trip-minutes`.

## Route plan command and verification (tasks 2.1 to 2.5)

- Migration `0017` upgrades and downgrades cleanly; `alembic check` reports no drift.
- Core check on 300 Ecoservice stops and 15 trucks: both plans serve the same 300 stops, none visited twice, no trip over capacity; 614 km vs 861 km baseline (28.7%), 1.4 s.
- `route_plan --carrier "Kauno švara" --date 2026-09-16 --max-iterations 500`: 1,288 stops, 0 unserved, 30 trucks; optimised 2,433.9 km, 144 trips, 0 overtime; baseline 2,752.3 km, 134 trips, 1,077 overtime minutes; saved 318.4 km (11.6%); 8.8 s.
- Rerun with `--seed 5` replaced the plan (one row, new id). A forced solver failure and a forced write failure (after the old plan was deleted in the transaction) both left the stored plan unchanged. Rebuilding the collection plan of the date left the route plan intact and `verify` still passed.
- Same inputs, parameters and seed twice: identical checksum of the stored trips and stops.
- Exit code 1 and nothing changed for: missing `--carrier`, missing `--date`, invalid date, date without collection plan, carrier without stops, carrier without an available truck (trucks set unavailable, then restored).
- `verify`: exit 0 on a fresh plan; after adding 50 km to one stored trip it exits 1 ("summary distance ... differs from the trips' sum"); exit 1 for a carrier without a stored plan.

## Read API (task 3.1)

Against the backend on the mapped port:

| Request | Result |
|---|---|
| `GET /route-plans/available` | 200, `[{"date":"2026-09-16","waste_carrier":"Kauno švara"}]` |
| `GET /route-plans?date=2026-09-16&waste_carrier=Kauno švara` | 200, summaries, parameters, 30 trucks with ordered trips and stops |
| `GET /route-plans?date=2026-09-17&waste_carrier=Ecoservice` | 404 "Route plan not found" |
| `GET /route-plans?date=2026-13-01&waste_carrier=Ecoservice` | 422 |
| `GET /route-plans?waste_carrier=Ecoservice` | 422 (date required) |

## Map page and end-to-end run (tasks 4.x, 5.x)

Plans stored for 2026-09-16 with defaults (1,000 iterations, seed 0), then `verify` exit 0 for all three:

| Carrier | Stops | Unserved | Optimised km | Baseline km | Saved | Trips (opt / base) | Overtime min (opt / base) | Solve |
|---|---|---|---|---|---|---|---|---|
| Ecoservice (102 demo trucks) | 2,613 | 10 | 11,803.8 | 15,401.1 | 3,597.2 km (23.4%) | 434 / 429 | 0 / 4,034 | 23 s |
| Ekonovus (95) | 2,305 | 0 | 11,422.8 | 14,290.9 | 2,868.1 km (20.1%) | 435 / 422 | 0 / 3,933 | 28 s |
| Kauno švara (30) | 1,288 | 0 | 2,433.9 | 2,752.3 | 318.4 km (11.6%) | 144 / 134 | 0 / 1,077 | 9 s |

(Kauno švara was planned with 500 iterations during testing; the Ecoservice and Ekonovus rows use the defaults.)

- Ecoservice's ten unserved stops each need more than 20 m3 (the largest demo truck); the page lists them.
- The demo fleet is not undersized, so the optimised plans have no overtime while the nearest-neighbour baseline has 1,000 to 4,000 minutes.
- `/admin/routes` was checked in headless Firefox (no real browser tool in this session): navigation entry `Maršrutai`, plan selector, savings panel (figures match the CLI: 11,824.2 vs 15,370.2 km, 437 vs 431 trips, 103 trucks, 0 vs 3,579 min for the earlier Ecoservice run), unserved list, truck list, and the map with its zoom control and numbered stop markers of the selected truck.
- Not confirmed: the route lines, stop circles and landfill circles are WebGL layers, and headless Firefox does not paint them (the existing map-analytics page is also blank there). A person needs to look at the map in a normal browser. The empty state (no stored plan) and the fresh-checkout import were not exercised either.
- Bug found and fixed on the way: MapLibre's stylesheet gives the map element `position: relative`, which overrode the Tailwind class and left the map at height 0; the page now sets the position inline.
