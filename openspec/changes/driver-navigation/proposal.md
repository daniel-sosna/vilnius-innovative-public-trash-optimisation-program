# Proposal

## Why

The route planning screen calculates road-following routes per truck, but nobody can follow one. A waste-truck driver needs a phone screen that guides the truck from stop to stop and records how full each bin was before it was emptied. That observation is the only way to get measured fill into `bin_hist`; today fill is predicted or synthetic. This completes the end-to-end workflow: prediction, route calculation, driving, observation.

## What Changes

- New mobile-first Driver screen at `/driver/:truck_id`, outside `AdminLayout`, with minimal chrome. The `Vairuotojas` button on the role page leads to a truck picker (`/driver`) that lists the trucks routed for the selected day.
- The Driver uses the application-wide project date and follows the route of its forecast day (T+1).
- New backend `GET /driver/trucks` and `POST /driver/route`: read the newest route calculation of the forecast day from the planning screen's run memory (PyVRP order, OSRM road geometry), and expand each service stop to every bin of the truck's carrier at the site. They never run prediction or route calculation.
- New backend `POST /driver/service`: records a successful service of all bins of one stop, each with an observed fill level 0-4, as `bin_hist` rows in one all-or-nothing request; the server assigns the timestamp.
- Driver workflow as an explicit state machine (`idle`, `preparing_route`, `navigating`, `at_bin`, `saving_service`, `completed`, `error`): the truck is animated along the road geometry with a follow camera and heading, pauses at each stop, steps through the stop's bins one at a time (five large fill buttons, tap to advance, back to correct), shows an all-done view, saves the stop together on confirm, and resumes.
- **BREAKING (data contract):** `bin_hist.fill_level` is widened from 0-3 to 0-4 by migration 0020, so that `4 = overflowing` can be stored. Existing rows remain valid.

## Capabilities

### New Capabilities
- `driver-navigation`: Driver truck list, route request, navigation screen behaviour, service recording and their error states.

### Modified Capabilities
- `collection-records`: `bin_hist.fill_level` accepts NULL or 0 through 4 instead of 0 through 3.

## Impact

- Backend: `interfaces/driver/` router and schemas, `services/driver_route.py`, `services/driver_service.py`; a read accessor in `services/demo_driving.py` (the run memory also records each run's forecast day); `main.py` router registration; Alembic `0020`; `models.py` check constraint; level 4 counted by the analytics agent.
- Frontend: `pages/driver/` (picker, screen, API client, workflow reducer, map, panels), `App.tsx` routes, role-selection link, a small shared route-geometry helper.
- Docs: `docs/data-model.md` (fill range), `docs/driver.md`, README feature row and docs index.
- No new dependencies, services or deployments.

## Material uncertainties and assumptions

- **Routes are transient.** Calculated routes exist only in the backend's memory (newest three runs, one hour, one worker; lost on restart). An administrator runs the calculation on `/admin/routes` for the selected date shortly before driving. Stored route plans (`route_plans`) are not used: they have no road geometry.
- **Load mismatch.** The calculation sizes loads from the due bins only, but the truck empties every bin of its carrier at a site, and the driver records all of them.
- **Service timestamp is wall-clock time**, not the simulated project date.
- **Landfill returns** are driven but are not stops; the route ends at the last service stop.
- **No authentication.** The truck comes from the URL.
- **Fill range change.** The migration alters a check constraint on an existing table. Rollback is refused when rows with level 4 exist.
