# Tasks

No automated tests are added (project rule). Non-UI logic is verified with the repeatable commands below; manual evidence goes into `openspec/changes/route-plan/verification.md`.

## 1. Demo fleet and spike (decides whether the approach holds)

- [x] 1.1 Add `pyvrp` to `backend/pyproject.toml` and the lock file; rebuild the backend image and verify `import pyvrp` works and `numpy` is still 1.26.4 (`docker compose exec backend uv run python -c "import numpy, pyvrp; print(numpy.__version__)"` and `importlib.metadata.version("pyvrp")`).
- [x] 1.2 Implement the demo-fleet command `python -m app.interfaces.demo_fleet --date YYYY-MM-DD` (sizing from `get_plan` totals, capacity mix, landfill round-robin, `DEMO ` prefix, seeded, replaces only its own trucks, exit codes per the `demo-fleet` spec); verify with a stored plan: it prints trucks per carrier, a second run gives the same trucks without duplicates, and a hand-entered truck is untouched.
- [x] 1.3 Build one collection plan for a September date (existing command, about 1 minute) and run the fleet command against it; record per-carrier stop counts, total load and fleet size in `verification.md`.
- [x] 1.4 Spike: in a throw-away script under the scratchpad, build the haversine matrix and the PyVRP model (reload depots, per-truck landfill, soft overtime) for the largest carrier of that date; verify on a small hand-checked instance that capacity per trip, reloads and overtime behave as the design assumes, then record the solve time for the real instance in `verification.md`. If PyVRP does not behave or is too slow, stop and update the design and specs before continuing.
- [x] 1.5 Sweep the overtime penalty over 1, 3, 10 and 30 on that instance; record km, trips, trucks used and overtime for each in `verification.md`, fix the default penalty and the iteration limit from the result, and update the defaults in the design if they differ.

## 2. Optimisation core and stored plan (computed, stored, verified from the command line)

- [x] 2.1 Add the migration `0017` and models for `route_plans`, `route_trucks`, `route_trips` and `route_stops` per the design; verify `alembic upgrade head` and `alembic downgrade -1` run cleanly on the dev database.
- [x] 2.2 Implement `app/optimization/` (distance/duration matrix, PyVRP model, nearest-neighbour baseline, metrics for both plans, oversize-stop handling), as pure functions without database access; verify by running it from a script on the spike instance and checking that both plans serve the same stops and that no trip exceeds its truck's capacity.
- [x] 2.3 Implement `app/services/route_plan.py` (read eligible trucks and the carrier's stops, call the optimiser, replace the (date, carrier) plan in one transaction, report excluded trucks and unserved stops); verify that a rerun replaces the plan, a forced failure leaves the previous plan unchanged, and rebuilding the collection plan leaves the stored route plan intact.
- [x] 2.4 Implement the CLI `python -m app.interfaces.route_plan --carrier ... --date ...` with the parameter options and defaults from the spec, the summary output and the exit codes; verify each scenario of the `route-planning` command requirements (missing argument, no plan for the date, no eligible truck, success, same seed twice gives the same plan).
- [x] 2.5 Implement the verification command `python -m app.interfaces.route_plan.verify --carrier ... --date ...` that reads the stored plan and checks the invariants (each due stop in exactly one trip or listed as unserved, trip load within capacity, summary figures match the trips, saving equals the difference); verify it exits 0 on a fresh plan and 1 after a deliberately altered row.
- [x] 2.6 Document in `docs/data/route-plan.md` the route-plan, verify and demo-fleet commands, their options and defaults, the assumptions (haversine and detour factor, speed, service and unloading time, shift, penalty, demo fleet is invented, loads predicted from synthetic data) and the runtime; add the new tables to `docs/data-model.md`; add the module rows to the README pipeline table and the docs index.

## 3. Read API

- [x] 3.1 Implement the router `GET /route-plans` and `GET /route-plans/available` with the response shapes from the `route-plan-viewing` spec, a read-only session, `404` for a missing plan and `422` for invalid parameters; verify with `curl` against the running backend for a stored plan, a missing plan, an invalid date and an empty listing, and record the commands in `verification.md`.

## 4. Map page

- [ ] 4.1 Add the `Maršrutai` navigation entry, the `/admin/routes` route and the plan selector fed by `/route-plans/available`, with the empty state naming the command; verify in the browser with a stored plan and with none.
- [ ] 4.2 Draw the selected plan on the map (colour per truck, landfill, numbered stops, lines between consecutive points, truck selection with highlight and trip list, unused trucks); verify in the browser with a plan of several trucks and several trips.
- [x] 4.3 Add the savings panel (both plans' km, trips, trucks used, overtime, saving in km and %), the unserved and excluded counts, and the caveat lines about synthetic loads and straight-line estimates; verify the figures against the CLI summary for the same plan.
- [x] 4.4 Add the page row to the README features table and note the URL in `docs/data/route-plan.md`; verify the links resolve.

## 5. Integration

- [ ] 5.1 Run the full demo path on a fresh checkout state (import, collection plan, demo fleet, route plan for the largest carrier, verify command, open the map) and record the evidence, the solve time and the savings figures in `verification.md`.
- [x] 5.2 Run `openspec validate route-plan --strict` and fix any findings; check the three docs touched stay consistent with the specs.

## Workflow follow-up

- Archive the change with `/opsx:archive` after review.
