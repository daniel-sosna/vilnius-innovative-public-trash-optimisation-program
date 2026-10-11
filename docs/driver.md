# Driver

Mobile screen at `/driver` (truck picker) and `/driver/:truck_id` that follows a stored route plan stop by stop and records each bin's fill level. Behaviour is specified in [`driver-navigation`](../openspec/specs/driver-navigation/spec.md).

## Prerequisites

A Driver run needs stored data for the plan date, built in this order (see [collection plan](data/collection-plan.md) and [route plan](data/route-plan.md)):

```bash
docker compose exec backend uv run python -m app.interfaces.collection_plan --date 2026-09-15
docker compose exec backend uv run python -m app.interfaces.demo_fleet --date 2026-09-16
docker compose exec backend uv run python -m app.interfaces.route_plan --carrier "Ecoservice" --date 2026-09-16
```

Without them the screen shows "no route data". Only a truck of the planned carrier that has a trip gets a route; the first trip is driven.

## Check a route

```bash
docker compose exec backend uv run python -m app.interfaces.driver.check --truck-id N
```

Builds the truck's route from the stored plans and prints stops, bins per stop and path size. Exit 0 when the route is valid, 1 otherwise (unknown truck, no plan, invalid path).

## Assumptions

- **Plan date is fixed.** `DRIVER_PLAN_DATE` in [`driver_route.py`](../backend/app/services/driver_route.py) is the only place that holds it. A date selector will replace it.
- **Navigation is mocked.** `MockNavigationService` ([`navigation.py`](../backend/app/services/navigation.py)) returns one fixed real-road path of 1,266 points through Vilnius and spaces the trip's stops evenly along it. The stop positions on the map, the road path and the truck position are simulated; bins, their order and identifiers are real. A trip needs fewer stops than the path has points.
- **Path data.** [`driver_road_path.geojson`](../backend/app/services/data/driver_road_path.geojson) was exported once from the public OSRM `route` service (full overview geometry) over fixed Vilnius waypoints. Road data © OpenStreetMap contributors (ODbL). The app never calls OSRM.
- **All carrier bins at a stop are recorded**, due or not: the truck empties every bin of its carrier at a site.
- **One save per stop.** `POST /driver/service` stores the stop's rows in one transaction with the server's Europe/Vilnius time. Repeating a request after a lost response can store a second row, because the unique key only collapses identical timestamps.
- **No authentication:** the truck comes from the URL.
