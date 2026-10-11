# Design

## Context

- `get_plan(session, date, carriers=[carrier])` returns the carrier's due stops with coordinates and `overall_predicted_fill_m3`. `collection_stops` are deleted and recreated whenever the collection plan of a date is rebuilt, and a `bins` import empties them.
- `trucks` has `max_volume_m3`, `waste_carrier`, nullable `landfill_id`, `available` and soft `deleted`. No table references `trucks`. The database holds no trucks and no stored collection plan; there are 3 landfills (two with approximate coordinates).
- `app/optimization/` exists and is empty. There is no routing engine and no distance source. Backend CLIs live under `app/interfaces/<name>/`, services under `app/services/`, migrations in `backend/alembic/versions/` (last is `0016`).
- Pinned `numpy==1.26.4` (the ML stack), Python 3.12. A dry run of `uv pip install` shows that `pyvrp==0.14.0` installs without changing numpy, whereas `ortools` would upgrade numpy to 2.x.
- PyVRP 0.14.0 exposes, on its vehicle type, `reload_depots`, `max_reloads`, `shift_duration`, `max_overtime`, `unit_overtime_cost`, a start and end depot, and capacity (checked in the wheel's type stubs). Those cover multi-trip, per-truck landfills and soft overtime without custom modelling.
- The frontend has MapLibre components, Lithuanian copy, and admin pages under `/admin/...`.

## Goals / Non-Goals

**Goals:**
- One solver, one baseline, one stored plan format, usable from CLI, API and map.
- A solve that finishes in minutes for the largest carrier (about 2,600 stops on the demo date) and is repeatable.

**Non-Goals:**
- Road-network routing, live data, re-planning, urgency, waste types, a UI trigger, background jobs, a separate service.
- Balancing work across trucks beyond what the overtime penalty does.

## Decisions

### D1. PyVRP as the solver, in-process
PyVRP (hybrid genetic search) is the single optimisation approach. It models the problem directly: one vehicle type per truck with `capacity`, its landfill as start and end depot, the landfill as a reload depot (multi-trip), `shift_duration` with `max_overtime` and `unit_overtime_cost` (soft overtime). It installs next to `numpy==1.26.4`.
Alternatives: OR-tools (forces numpy 2, would affect the ML stack; multi-trip needs hand-built dummy nodes); VROOM or an external service (violates "no separate deployments"); custom heuristic (contradicts the "meaningful sophistication" principle and gives no benchmark).
Confirmed in the spike before anything else is built, because the whole plan rests on it.

### D2. Cost model, in one unit
Objective = distance cost + overtime cost. The solver works in integers: distances in metres, durations in seconds, `unit_distance_cost` 1 per metre. One overtime minute costs `overtime_penalty` km, which is `overtime_penalty × 1000` cost units per minute, so `unit_overtime_cost` per second is `round(overtime_penalty × 1000 / 60)` (default 10 gives 167, a 0.2% rounding error). `unit_duration_cost` stays 0, so only distance and overtime are priced. Idle trucks cost nothing (no `fixed_cost`), matching the decision that idle trucks are acceptable.
`max_overtime` is a hard cap, set large (for example 12 hours) so overtime is limited only by its price. The penalty is swept over 1, 3, 10 and 30 on a real carrier-day (verification.md): the km-versus-overtime curve is flat, so the default stays 10.

### D3. Distance and duration from haversine
One symmetric matrix of haversine distances times a detour factor (default 1.3) between all stops and landfills. Duration = distance / average speed (default 30 km/h) + service time at the arrival stop (default 5 min per stop) in the matrix cell, and unloading time (default 15 min) added to every edge that arrives at a landfill, because PyVRP charges a depot's service duration at the start and at reloads but not at the end of the last trip. Depot service stays 0. At about 2,600 stops the matrix is about 7 million cells and fits in memory as NumPy arrays.
Alternatives: OSRM container (new service, Lithuania extract, more setup; rejected for this milestone); public OSRM (cannot give a large matrix; external dependency). The saving is reported against a baseline with the same metric, so a systematic distortion mostly cancels. Distances are labelled estimates everywhere.
Defaults for speed, detour, service and unloading time and shift length (default 8 h) are assumptions, stored with the run.

### D4. Trucks as vehicle types, not individual vehicles
Each eligible truck becomes a vehicle type with `num_available=1`, so individual capacity, landfill, and name map back to a stored truck. With many trucks, symmetric duplicates are avoided because trucks differ by capacity and depot or are interchangeable at the price of a slower search; if the spike shows it is too slow, trucks with identical capacity and landfill are grouped into one vehicle type with `num_available=n` and names assigned after the solve.

### D5. Determinism: an iteration limit, not wall time
The stopping criterion is a maximum number of iterations (default 1,000, about 60 s for the largest carrier in the spike) and a fixed seed, not a time limit, so the same inputs and parameters give the same plan on the same machine. A wall-clock guard remains as a safety valve and, if it triggers, is reported in the output and stored in the run. The effort limit and seed are in the stored parameters.

### D6. Baseline: nearest-neighbour, trucks taking turns
Implemented in plain Python in `app/optimization/`, on the same matrix and the same truck, capacity, trip and shift rules. Each truck in turn drives to the nearest unserved stop that fits in its remaining capacity; when none fits it returns to its landfill, unloads and starts a new trip. A truck stays in the rotation until no stops remain. It does not optimise overtime; overtime is measured afterwards with the same shift rule. It is a single reference, not a second solver.

### D7. Oversize stops removed before solving
A stop whose load exceeds the capacity of every eligible truck is removed before solving and reported as unserved. This is the only way a stop is left out. Stops with load 0 are kept (they are visited because they are due).
Load is converted to an integer (litres or 1 dm³) for the solver, rounding up so a trip never exceeds the truck. The rounding is documented.

### D8. Storage: copied data, no foreign keys to the collection plan or trucks
Four tables, created by one Alembic migration:

```
route_plans    id, date, waste_carrier, created_at, parameters JSONB,
               summary JSONB (optimised + baseline + saving),
               unserved JSONB (stop copy + reason), excluded_trucks int
               UNIQUE (date, waste_carrier)
route_trucks   id, plan_id FK CASCADE, truck_id (no FK), name, max_volume_m3,
               landfill_id (no FK), landfill_name, landfill lat/lon, position
route_trips    id, route_truck_id FK CASCADE, seq, load_m3, distance_km, duration_min
route_stops    trip_id FK CASCADE, seq, site_id (no FK), address, lat, lon,
               load_m3, bin_count
```

Stops copy their data; nothing references `collection_stops`, `sites`, `bins` or `trucks`. A collection-plan rebuild, a site deletion or a seeded-fleet replacement therefore does not affect a stored plan. Replace = delete the (date, carrier) row (cascade) and insert in one transaction.
Alternative considered: FK to `collection_stops` (rejected: the rebuild deletes and recreates stops, so the plan would be lost or blocked). JSON for the whole plan (rejected: harder to query for the map, no real gain over four small tables).
The baseline's per-truck routes are not stored, only its summary figures (the stored comparison). This keeps the data model small; showing the baseline on the map is out of scope.

### D9. Service layer and CLI follow `collection_plan`
- `app/optimization/` holds pure computation: the matrix, the PyVRP model, the baseline, and the metrics. It takes plain Python/NumPy inputs and returns plain results, with no database access, so it can be run by a script.
- `app/services/route_plan.py` reads inputs (`get_plan`, trucks), calls the optimiser, writes/reads the stored plan.
- `app/interfaces/route_plan/` holds the CLI (`python -m app.interfaces.route_plan --carrier ... --date ...`), mirroring `collection_plan`'s argument handling, logging and exit codes, and the read router.
- `--date` is the plan date itself (the date whose collection plan exists), unlike the collection-plan command that takes "today". The help text says so.

### D10. Fleet seeding sizes from load
`app/interfaces/demo_fleet/` is a command that reads `get_plan` totals per carrier. For each carrier: `trucks = ceil(1.2 × total_load / (mean_capacity × trips_per_shift))`, with `trips_per_shift = shift_minutes / assumed_trip_minutes` (default trip 90 minutes, a rough estimate). Capacities are drawn from the mix {10, 16, 20 m³} by seed, landfills round-robin over stored landfills. Names are `DEMO <carrier> <n>`. Replacement deletes trucks whose name starts with `DEMO ` (hard delete; nothing references trucks, and stored route plans copy truck data), then inserts. The estimate is deliberately rough: the spike checks the result and the parameters are tuned from it.

### D11. Read API and map page
- `GET /route-plans?date=&waste_carrier=` and `GET /route-plans/available`, in a new router with its own read-only session pattern like `collection_session`.
- A new admin page `/admin/routes` reuses the MapLibre setup of the existing map components. Route lines are drawn as GeoJSON line layers with a colour per truck and numbered point symbols for stops. A side panel lists trucks, trips and the savings. No new frontend dependency.
- Straight lines between consecutive points; the page says that they are estimates.

### D12. Documentation
A single topic file `docs/data/route-plan.md` covers the route-plan and fleet commands, parameters, assumptions and how to run the verification. The README index gets one row; behaviour stays in the specs.

## Risks / Trade-offs

- **Solve time at about 2,600 stops** → measured in the spike: about 90 s for 1,500 iterations with 103 trucks. The iteration limit is set from it.
- **PyVRP semantics around soft overtime and reloads** (for example how `max_overtime` interacts with reloads, or reload cost) → verified in the spike with a small hand-checked instance; if it does not behave, the shift is modelled with a hard `max_duration` at shift plus an overtime allowance and the penalty through `unit_duration_cost` is revisited, and the specs and design are updated before continuing.
- **Penalty too high or too low** → swept in the spike; the default is fixed from the curve. A too-high penalty inflates km for a few minutes of overtime.
- **Light days leave trucks idle** → accepted; the demo date is chosen so the fleet is busy, and the seed sizes the fleet for that.
- **Seeded fleet is invented** → labelled as demo data; real fleet data would replace it without changing the model.
- **Straight lines and haversine** → labelled as estimates; map looks less realistic than road geometry. OSRM can come later behind the same matrix function.
- **Rounded loads** → loads rounded up to whole litres can make a stop that barely fits count as oversize by a litre; negligible and documented.
- **Landfill coordinates are approximate** (two of three) → distances to the landfill are approximate; stated in the docs.
- **Determinism across machines** → the same machine only; PyVRP's floating-point and thread behaviour may differ elsewhere.

## Migration Plan

One additive Alembic migration (`0017`) creating the four tables; downgrade drops them. No data is changed. The new dependency is added to `pyproject.toml` and the lock file; the image is rebuilt.

## Open Questions

- The exact defaults for average speed, service and unloading time, shift length, detour factor and the penalty are fixed from the spike; the specs state that defaults exist and are documented, not their values.
