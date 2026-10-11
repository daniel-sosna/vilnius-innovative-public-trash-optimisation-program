# Route plan

For one carrier and one date, the route plan assigns the carrier's due stops to its trucks as ordered trips and compares the result with a naive baseline. Behaviour is specified in [`route-planning`](../../openspec/specs/route-planning/spec.md), [`route-plan-viewing`](../../openspec/specs/route-plan-viewing/spec.md) and [`demo-fleet`](../../openspec/specs/demo-fleet/spec.md).

```bash
docker compose exec backend uv run python -m app.interfaces.demo_fleet --date YYYY-MM-DD
docker compose exec backend uv run python -m app.interfaces.route_plan --carrier "Ecoservice" --date YYYY-MM-DD
docker compose exec backend uv run python -m app.interfaces.route_plan.verify --carrier "Ecoservice" --date YYYY-MM-DD
```

`--date` is the **plan date** (the date the [collection plan](collection-plan.md) was stored under, `T+1`), not "today". Build the collection plan first. A run takes about one minute for the largest carrier (about 2,600 stops, 100 trucks).

Stored plans remain available through the read-only `/route-plans` API. The administrator `Maršrutai` page runs current predictions and navigation; see [route planning setup](../development.md#route-planning).

## Route plan command

| Option | Default | Meaning |
|---|---|---|
| `--carrier`, `--date` | required | Carrier and plan date |
| `--speed-kmh` | 30 | Average driving speed |
| `--detour-factor` | 1.3 | Road length as a multiple of the straight-line distance |
| `--service-min` | 5 | Minutes at each stop |
| `--unload-min` | 15 | Minutes for each unloading at the landfill |
| `--shift-min` | 480 | Shift length; time beyond it is overtime |
| `--overtime-penalty` | 10 | Cost of an overtime minute, in km of driving |
| `--max-iterations` | 1000 | Solver effort |
| `--seed` | 0 | Solver seed |

The command replaces the stored plan of the carrier and date in one transaction and prints the parameters, both plans' figures and the saving. It exits 1 on invalid arguments, a date without a collection plan, a carrier without stops or without an eligible truck, a database failure or a solve failure, and then changes nothing.

- **Trucks used:** the carrier's trucks that are available, not deleted and have a landfill with coordinates. Others are counted as excluded.
- **Trips:** a trip starts and ends at the truck's landfill, and its stops' `overall_predicted_fill_m3` fit the truck's `max_volume_m3`. A truck unloads between trips. A stop larger than every truck is reported as unserved.
- **Solver:** [PyVRP](https://pyvrp.org) in the backend process (one vehicle type per truck, the landfill as depot and reload depot, soft overtime). Costs are metres of driving plus overtime seconds priced by `--overtime-penalty`. The stop is an iteration count, not wall time, so the same inputs, parameters and seed give the same plan on the same machine. A 900 s wall-clock limit is a safety valve and is reported if reached.
- **Baseline:** nearest neighbour. Trucks take turns; on its turn a truck drives to the nearest unserved stop that still fits, repeatedly, and returns to unload when none fits. Overtime is measured with the same shift rule. Only its figures are stored.

## Demo fleet

`demo_fleet --date ...` replaces the trucks named `DEMO <carrier> <n>` with a fleet sized from the stored collection plan: `trucks = ceil(1.2 x load / (mean capacity x trips per shift))`, with trips per shift = shift / assumed trip length. Other trucks are not touched. Options: `--capacities` (default 10,16,20 m³, drawn at random), `--shift-minutes` (480), `--trip-minutes` (90, only used for sizing; a larger value makes a busier day), `--seed`. Landfills are assigned round-robin.

## Assumptions

- **Distances are estimates:** haversine distance times the detour factor, not road routes. Savings compare plans under the same estimate. The map draws straight lines.
- **Speed, service, unloading, shift and detour factor** are assumed values, stored with every plan.
- **The demo fleet is invented**, not real fleet data.
- **Loads are predictions** from the model trained on synthetic history, with assumed fill shares (see [collection plan](collection-plan.md#assumptions)).
- **Landfill coordinates** are approximate for two of the three landfills.
- **Light days leave trucks idle:** there is no fixed cost per truck and no balancing.
- **Loads are rounded** to whole litres (stops up, capacities down).

## Verification

`route_plan.verify` reads the stored plan and checks that every due stop is planned once or listed as unserved, no trip exceeds its truck, and the summary matches the stored routes. It exits 0 when all hold and 1 otherwise.
