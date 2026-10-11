# Driver

Mobile screen at `/driver` (truck picker) and `/driver/:truck_id` that follows a truck's calculated road route stop by stop and records each bin's fill level. Behaviour is specified in [`driver-navigation`](../openspec/specs/driver-navigation/spec.md).

## Before a Driver run

1. Select the project date in the admin calendar. The Driver follows the route of the next day (T+1).
2. On `/admin/routes`, run the route calculation for that date and wait until the truck table is filled (see [Development](development.md) for the prediction and routing prerequisites).
3. Open `/driver` on the same browser (the date is stored per browser) and pick a truck.

Only trucks with a route in the newest calculation of that day are listed.

## Assumptions

- **Routes are transient.** The Driver reads the planning screen's run memory: the newest three runs, kept for one hour, in one backend worker, lost on restart. Stored route plans (`route_plans`) are not used, because they have no road geometry.
- **Road geometry is real**, from the road-routing service used by the calculation (OSRM). Landfill returns between and after trips are part of the path but are not stops; the route ends at the last service stop.
- **Truck movement is simulated** along that path at 100 m/s (`DEMO_SPEED_MPS` in [`use-route-animator.ts`](../frontend/src/pages/driver/use-route-animator.ts)) so a route can be shown in minutes.
- **All carrier bins at a stop are recorded**, due or not: the truck empties every bin of its carrier at a site. The calculation sized loads from the due bins only.
- **One save per stop.** `POST /driver/service` stores the stop's rows in one transaction with the server's Europe/Vilnius wall-clock time, not the project date. Repeating a request after a lost response can store a second row, because the unique key only collapses identical timestamps.
- **No authentication:** the truck comes from the URL.
