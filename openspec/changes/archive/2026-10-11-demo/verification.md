# Demo verification

## Developer confirmation

The developer confirmed: “yes i have verified all my self you can compltre them”.
All 28 tasks are recorded complete on that basis. The confirmation covers the
integrated workflow, failure/cleanup cases and requested presentation changes.
Detailed additional measurements or logs were not supplied; the evidence below
distinguishes agent observations from developer-reported verification. No further
application checks were run by the agent.

## Prerequisites — 2026-10-11

- Configured data directory: `backend/data/` (default; no override).
- Collection exports: `sites_202610092000.csv`, `bins_202610091935.csv`, `bin_hist_202610091935.csv` are present.
- Inference inputs: `bin_days_20231010_20261009_enriched.csv`, `bins_202610091935.csv`, `bin_population.csv` are present.
- Product: `ml/september-fill-predictor/product/model.joblib` and `district_aliases.json` are present.
- `validate_demo_paths()` resolves all configured paths successfully; a controlled missing-product setting fails with both missing artifact paths and configuration guidance.
- Trusted model loaded successfully in an isolated Python 3.12 environment. Its payload contains `name`, `preprocessing`, `model`, `metadata`; model is CatBoost and training ends 2026-08-31.
- Embedded metadata records numpy 1.26.4, pandas 2.2.3, scipy 1.15.3, scikit-learn 1.5.2, catboost 1.2.8, joblib 1.4.2. The isolated load used these versions and holidays 0.72 from the existing research requirements.
- Developer waived separate delivered requirements/manifest files; compatibility can be checked against embedded model metadata.
- No inference, source generation, training or collection-plan writes performed.

## Runtime evidence before developer verification handoff

Docker access uses `sg docker -c '<docker command>'`. The stack was built and started. The backend image installs locked inference dependencies and imports the portable predictor and API. The supplied product loads as CatBoost. The existing database contains 21,951 bins and 5,730 collection stops, so no table import was performed.

The real September 14 endpoint request completed in 22.25 seconds: forecast September 15, 21,951 evaluated bins, 9,270 due bins, zero unmappable bins. A timestamp request returned 422. An overlapping prediction returned 409 while a fleet read returned 200. This establishes real inference but does not establish the five-minute client wait scenario: the supplied CSV starts in June 2026 and completed much faster.

The developer authorized creating three available fleet records through the existing API: `Demo 1`, `Demo 2`, `Demo 3` (IDs 1–3), each with 20 m³ capacity, Ecoservice and landfill ID 1. These are stored demo trucks; mock route assignment makes no carrier/capacity feasibility claim.

## Developer-owned verification

The developer explicitly requested: “I will verify. Do not do any verification yourself.” No further runtime checks, build, lint, validation or browser verification are run by the agent after that instruction. The in-app browser was unavailable; no fallback browser was used. Implementation entries with required verification are complete based on the developer confirmation above. The following checklist records the scope covered by that confirmation.

- Run frontend build/lint and OpenSpec validation (task 5.3).
- Run `python -m app.interfaces.demo --date 2026-09-14 --navigation` in the backend environment and compare with the endpoint.
- Confirm path overrides/mounts and startup with absent demo artifacts.
- Exercise a full browser run: selection → real prediction → markers → road navigation → four-second drawing → paginated truck table → truck following.
- Exercise September 30 → October 1, storage denial/invalid storage, navigation/refresh persistence, keyboard calendar and 320px layouts.
- Exercise lock release, duplicate start, restart, date changes, missing model, zero due/unmappable bins, missing fleet, navigation/map/drawing failure and leaving during requests/animation. Use response interception only for unavailable failure scenarios.
- Check source/model hashes and saved collection-plan records remain unchanged. `/tmp/demo-input-sha256.txt` and `/tmp/demo-plan-counts.txt` contain baselines captured before the verification handoff; these temporary files are session-local.
- Confirm existing fleet/site pages and Map Analytics layer/camera/agent behavior.
- Record measured dates, counts, duration, outcomes and any errors here. Do not mark a required check complete solely from implementation notes.

## Demo corrections handoff

The developer requested road-following paths, individual bins, 150 trucks,
five-row result pages and removal of the schematic-route disclaimer and
Aptarnauti label. Code and change artifacts reflect these requirements.
The explicit fleet population command created 147 additional records and
enabled Demo 1–150. It was a requested data mutation, not a verification run.

Road geometry uses the configured OSRM endpoint, with request pacing, finite
deadlines and errors instead of straight-line fallback. No road requests,
build/lint, automated checks or UI verification were performed by the agent.
Developer checks: road alignment, individual bin rendering, up to 150 assigned
routes, 30 five-row pages for a 150-truck result, stable map/pagination reset,
removed labels, public-service error handling and unchanged Map Analytics
clustering.

## Truck-following corrections handoff

The driving page uses `GET /demo/driving-route` for OSRM road legs and snapped
stops, follows the truck with the camera and varies slower travel and collection
pause timings. Its title is `Šiukšliavežės sekimas`. The stored truck name,
description, collection/completion text, color explanation and return/replay
buttons are removed. Shared navbar navigation and loading/error feedback remain.

Developer checks: road-aligned marker movement, camera following/final hold,
variable slower speed and pauses, collected-bin visuals, reduced motion,
missing truck/road-service failures, mobile layout and cleanup on navigation.
No road requests, build/lint, runtime checks or browser verification were
performed by the agent for these corrections.

## Continuous driving geometry correction

The route builder uses OSRM's full route overview as the geometry authority and
partitions that same path into adjacent legs sharing boundary vertices near the
ordered snapped waypoints. It does not join independently generated maneuver
endpoints or introduce straight-line connectors. The truck title is
`Šiukšliavežės sekimas`, and the extra prediction-duration sentence is removed.
Developer verification is confirmed above; no route requests or checks were run by the agent.

## Roundabout start

The driving fixture starts at the western roundabout arc at Geležinio Vilko /
A. Goštauto (`25.2610, 54.6937`), using the screenshot to locate the visible arc.
OSRM snaps this input to the road; the marker and camera use the returned path's
first coordinate. Developer verification of the starting position is confirmed above. No runtime or browser checks were run.

## Remaining road line

The driving animation trims the existing route source behind the truck's current
interpolated position, preserves future legs during movement and collection
pauses, and clears the route line at the final stop. Developer verification
is confirmed above; no runtime or browser checks were run.

## Predicted-bin appearance animation

The Demo map reveals eligible predicted markers in a separately shuffled order,
adding batches of 1, 1, 1, 2, 2, 2, 4, 4, 4 and subsequent triplets of doubled
batch sizes, capped at the mapped total. Each batch waits for map render
acknowledgement; its following delay decreases from 700 ms by a factor of 0.88
per batch-size group, with a 180 ms minimum. Existing markers stay visible, and
the displayed mapped count follows the reveal. Routing inputs retain their order.
Prediction feedback and controls remain active/locked until all markers render,
then navigation starts. Reduced-motion mode shows the complete set together.
Pending appearance timers are cancelled when the run stops or the page unmounts.

Developer checks: random spatial appearance, repeated batch sizes, slower pacing, exact final
marker count, navigation after final appearance, reduced motion and leaving
during the reveal. No build, lint, tests, runtime or browser verification was
performed by the agent for this change.
