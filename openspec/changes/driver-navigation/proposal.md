# Proposal

## Why

Admins can see stored route plans, but nobody can follow one. A waste-truck driver needs a phone screen that guides the truck from stop to stop and records how full each bin was before it was emptied. That observation is the only way to get measured fill into `bin_hist`; today fill is predicted or synthetic. A mocked but road-shaped vertical slice shows the end-to-end workflow (prediction, collection plan, route plan, navigation, observation) before real routing exists.

## What Changes

- New mobile-first Driver screen at `/driver/:truck_id`, outside `AdminLayout`, with minimal chrome. The disabled `Vairuotojas` button on the role page leads to a minimal truck picker (`/driver`).
- New backend `POST /driver/route`: builds the driver's route from the truck's stored route-plan trip (stop order) and the collection plan (every bin of the carrier at each stop), for one hardcoded plan date constant. It reads database state only; it never runs prediction, route planning or filesystem CSV access.
- New `NavigationService` interface with one `MockNavigationService` implementation. It returns a hardcoded, real-road polyline (static GeoJSON in the repository) and places the stops along it. The real router replaces the mock without changing the screen.
- New backend `POST /driver/service`: records a successful service of all bins of one stop, each with an observed fill level 0-4, as `bin_hist` rows in one all-or-nothing request; the server assigns the timestamp.
- Driver workflow as an explicit state machine (`idle`, `preparing_route`, `navigating`, `at_bin`, `saving_service`, `completed`, `error`): the truck is animated along the road geometry with a follow camera and heading, pauses at each stop, steps through the stop's bins one at a time (five large fill buttons, tap to advance, back to correct), shows an all-done view, saves the stop together on confirm, and resumes.
- **BREAKING (data contract):** `bin_hist.fill_level` is widened from 0-3 to 0-4 by migration 0019, so that `4 = overflowing` can be stored. Existing rows remain valid.

## Capabilities

### New Capabilities
- `driver-navigation`: the Driver route request, mock navigation contract, navigation screen behaviour, service recording and its error states.

### Modified Capabilities
- `collection-records`: `bin_hist.fill_level` accepts NULL or 0 through 4 instead of 0 through 3.

## Impact

- Backend: new `interfaces/driver/` router and schemas, `services/driver_route.py`, `services/navigation.py` (interface + mock) and a static road-path data file; `main.py` router registration; Alembic `0019`; `models.py` check constraint.
- Frontend: new `pages/driver/` (picker, screen, API client, workflow reducer, map, panels), `App.tsx` routes, role-selection link, a small shared route-interpolation helper.
- Docs: `docs/data-model.md` (fill range), a new `docs/driver.md` entry for the plan-date constant, prerequisites and mock assumptions, README feature row.
- No new dependencies, services or deployments.

## Material uncertainties and assumptions

- **No global project date exists on this branch.** The plan date is one hardcoded constant in one place; a date selector is planned later and will replace it.
- **Mock positions are not real.** The static road path is fixed, so the N stops are spaced evenly along it. Bins, inventory numbers, waste types and order are real; map positions are mock.
- **Prerequisite data.** The Driver needs a stored collection plan, demo fleet and route plan for the constant date, and a truck with a trip. Without them the Driver shows the "no data" state.
- **One trip per truck.** Only the truck's first trip is driven; the landfill is not a stop.
- **All carrier bins at a stop are serviced.** The truck empties every bin of its carrier at a site (collection-plan spec), so the driver records a fill level for every bin of the stop, due or not. One stop is saved in one request after the driver reviews it.
- **No authentication.** The truck comes from the URL.
- **Fill range change.** The migration alters a check constraint on an existing table. Rollback is refused when rows with level 4 exist.
