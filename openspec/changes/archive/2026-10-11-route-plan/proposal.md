# Proposal

## Why

The collection plan says which sites a carrier must serve on a day, but not which truck goes where or in what order. The first route-optimisation milestone turns that list into a stored daily route for each truck, shows it on the map and measures how much driving it saves against a naive plan for the same stops. It is a complete slice that can be demonstrated through the real system.

## What Changes

- A **route-plan command** that, for one carrier and one date, reads the carrier's due stops (`get_plan`) and its trucks that are available, not deleted and have a landfill, and stores a plan: for each truck an ordered list of **trips**. A trip starts and ends at the truck's own landfill, and the summed stop loads (`overall_predicted_fill_m3`) never exceed the truck's `max_volume_m3`. The truck unloads at the landfill between trips, so every due stop is served.
- **Shift limit as a soft constraint.** A truck's day (driving, service at stops, unloading) has a shift length; time beyond it is overtime and costs about 10 km-equivalents per minute, so overtime appears only when every truck is already busy. Idle trucks are accepted.
- A stop that alone exceeds every truck is not planned and is reported as unserved with its reason. Trucks without a landfill are excluded and counted.
- A **baseline** for the same stops, trucks and rules: nearest-neighbour, trucks taking turns. The command stores and prints optimised vs baseline: kilometres, trips, trucks used and overtime.
- A rerun replaces the plan of (date, carrier) atomically. Route stops keep their own copy of site, address, coordinates and load, so a collection-plan rebuild does not invalidate a stored route plan.
- A **read API** for the stored plan and its summary, and an admin **map page** (Lithuanian UI) with one colour per truck, ordered stops, trip breakdown and the savings summary.
- A **fleet seed command** that creates a demo fleet per carrier, sized from the stored collection plan of a date, marked so it never touches hand-entered trucks.
- Out of scope: re-planning during the shift, live positions, urgency, waste-type restrictions, multi-carrier solving, a UI trigger or background jobs, road-network routing (OSRM).

## Capabilities

### New Capabilities

- `route-planning`: the daily route plan of a carrier: model, solving, baseline comparison, storage, summary and the command that computes it.
- `route-plan-viewing`: reading a stored route plan through the API and showing it on the admin map page.
- `demo-fleet`: the command that seeds a reproducible demo fleet sized from the stored collection plan.

### Modified Capabilities

None. Truck behaviour is unchanged; seeded trucks are ordinary trucks.

## Impact

- **Database:** new tables for route plans, trips and route stops (Alembic migration). Route stops reference sites loosely and copy the stop data, so they do not depend on `collection_stops`.
- **Backend:** a solver in `app/optimization/`, a service and CLI for the plan, a read router, a fleet seed CLI. One new dependency: the routing solver (PyVRP or OR-tools, chosen in the spike; must work with the pinned `numpy==1.26.4`).
- **Frontend:** a new admin page and navigation entry using the existing MapLibre components.
- **Shared contracts:** reads `get_plan` and the `trucks` table unchanged. The stored route plan is a new contract for the map and later milestones.
- **Docs:** a topic file under `docs/data/` for the commands and assumptions, plus the README index row.

## Material uncertainties and assumptions

- **Solver feasibility at scale.** A carrier has up to about 2,600 due stops on the demo date. The spike showed that PyVRP handles this size with multi-trip, per-truck landfills and soft overtime next to the numpy pin (see verification.md).
- **Distances are straight-line (haversine) times a detour factor**, not road distances. Kilometre figures are estimates, and the map draws straight lines. Savings are a ratio against a baseline using the same metric.
- **Time model values are assumed:** average speed, service time per stop, unloading time, shift length and the detour factor. They are recorded with each run.
- **Overtime penalty of 10 km per minute** is a starting value; the spike sweeps 1, 3, 10 and 30 and the value is fixed from the result.
- **Demo fleet is invented**, not real fleet data (truck sizes and landfill spread). Loads are predicted from synthetic history with assumed fill shares, so every figure is a simulation.
- **Lighter days leave trucks idle** by design (no fixed truck cost, no balancing).
- **The baseline is a choice.** Nearest-neighbour is conservative; a weaker one would inflate the saving.
- Solver runs are bounded by a time limit and a fixed seed; results are repeatable for the same inputs and parameters but may differ across machines.
