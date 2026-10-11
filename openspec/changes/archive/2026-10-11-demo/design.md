# Design

## Context

See `proposal.md` for motivation and the delta specs for observable behavior. `App.tsx` owns React Router routes; `AdminLayout` owns the navbar and gives Map Analytics a special viewport layout. Page-local `api.ts` modules call `/api`, and Vite strips that prefix before forwarding to FastAPI.

`AnalyticsMap` already owns configurable style loading, MapLibre workers, resize, error feedback and disposal. Its stable `MapLayerDefinition` registry supports updating data without recreating the map. It lacks an external readiness/animation completion interface.

`viptop_fill.csv_demo.predict_csv` reads immutable history in bounded batches and calls the delivered `FillPredictor`, which predicts T+1. It returns every registry bin's argmax fill level. `app.ml.fill_prediction` is an unrelated seeded mock used by the collection-plan CLI; this design leaves that CLI and its spec unchanged. API dependencies do not include model libraries, and the production Dockerfile does not copy `viptop_fill`. The configured product directory is absent locally. Collection CSV exports are present, but they do not replace the enriched ML history, population input or trained product.

## Goals / Non-Goals

**Goals:** Connect real inference to one filmable frontend pipeline, isolate temporary navigation and driving behavior, retain map instances across runs, and release UI resources reliably despite long inference.

**Non-Goals:** New job infrastructure, separate ML deployment, inference caching/precomputation or optimization, changes to model features/training, collection-plan persistence, road routing, carrier/capacity optimization, GPS or operational collection writes.

## Decisions

### 1. Date provider at the application root

Add a small React context/provider above the route tree and a reusable `useProjectDate()` hook. Store a validated `YYYY-MM-DD` string with bounds `2026-09-01` through `2026-09-30`; default to `2026-09-14`. Persist only the date in localStorage, handling storage failure. Use date components or UTC calendar arithmetic for T+1, never local timestamp conversion for the selected string.

Expose date updates and an owner-scoped, idempotent run lock. Reject date updates while locked, including if the calendar was open before Start. Demo acquires the lock synchronously before starting and releases it at every terminal outcome and unmount. An old callback cannot release a newer run's lock. Do not persist locks.

Add a September month grid to a small existing-style popover/dialog with keyboard-operable day controls, disabled month navigation and visible selected date. This supplies the requested month-only calendar without a general state framework or an unrestricted native date popup. Map Analytics consumes the provider without using it to alter existing API queries or analysis context. A provider at AdminLayout alone was considered, but an App-level provider meets application-wide access across route changes.

### 2. Real inference in the existing backend

Add `app/interfaces/demo/` schemas/router and a focused prediction service. Expose backend `POST /demo/predictions`, reached by frontend `/api/demo/predictions`. Request: `{project_date: '2026-09-14'}`. Response: `{project_date, forecast_date, evaluated_count, due_count, unmappable_count, bins}`. Each due bin carries `bin_id`, `site_id`, `fill_level`, nullable `latitude`/`longitude`, and useful stored address/carrier context.

Configure explicit server-side paths for the trusted product directory, enriched daily CSV, authoritative registry CSV and population CSV using backend settings, resolved against the configured data directory. Do not reuse research YAML paths that refer to repository-relative locations inside `/app`. Include the product's normalization artifact and match runtime dependencies to the versions embedded in the supplied model metadata; separate `requirements.txt` and `manifest.json` files are not prerequisites, as directed by the developer. Add only inference dependencies to the API environment/lock, not the research toolkit; copy `viptop_fill` into the image. Resolve dependency versions from the actual supplied product during implementation, without generating or loading untrusted replacement bundles.

Use the existing `predict_csv` path unchanged, passing T directly. Filter its argmax levels at `>2`. Validate the authoritative registry-to-database identity join; table imports preserve IDs, but a different export may not align. Read database context in a short read-only session after inference, rather than holding a database transaction through a five-minute CSV scan. Retain due bins with missing coordinates and report them; route only valid coordinates. Do not call `build_plan`, modify stored plans or overwrite model/source files.

Use a synchronous FastAPI handler so inference runs off the async event loop. Keep ML imports inside the inference boundary so missing optional prerequisites produce actionable endpoint errors without preventing other pages from starting. Use a single in-process inference guard for the demo backend to reject overlapping expensive runs with a busy error; release it in `finally`. This is a single-worker hackathon deployment, not a distributed scheduler.

Use a 15-minute prediction client deadline and ensure development server/preview proxy timeouts are no shorter. Routing can use a shorter finite deadline. The wait remains honest and indeterminate; no minimum artificial ML delay or result cache. Aborting fetch or leaving the screen does not guarantee stopping a synchronous backend CSV scan. Its completed output is discarded by the abandoned client. A later request may report busy until it finishes. A durable job/polling design adds infrastructure and is unnecessary for the accepted filming workflow.

### 3. Road-following navigation with 150 stored trucks

Expose backend `POST /demo/navigation` accepting `{forecast_date, bin_ids}` for the mappable predicted bins. Validate forecast range September 2 through October 1, unique stored IDs and usable coordinates; reject empty input. Re-read available, nondeleted trucks and bin/site context. Return `{forecast_date, source: 'osrm', routes}` with typed Pydantic and TypeScript DTOs.

A route contains `truck_id`, stored `truck_name`, `route_id`, ordered road `path: [{latitude, longitude}]`, and ordered `stops: [{site_id, bin_ids, latitude, longitude}]`. Counts derive from stop membership, not path vertices. The frontend maps the transport response to colors and counts once. `RoadNavigationService` implements the existing replaceable navigation contract.

Group bins into site stops, sort geographically with stable ID tie-breakers and partition contiguous groups among up to 150 eligible trucks ordered by ID. Keep only nonempty groups, assigning each input bin exactly once. The explicit `app.interfaces.demo.fleet` command supplies stored Demo 1–150 trucks without replacing unrelated fleet records. The developer authorized this fleet expansion.

Resolve paths through OSRM's route service with full GeoJSON geometry and the supplied stop order. This computes road travel paths; assignments remain a demo partition without carrier/capacity optimization. A one-stop route uses OSRM nearest-road snapping. Split oversized waypoint lists into overlapping chunks, carry available snap hints and reject disconnected geometry instead of inventing straight connectors. Missing fleet, service failures and unavailable road geometry fail explicitly while retaining predicted markers.

Default to `https://router.project-osrm.org`, configurable via `DEMO_OSRM_URL`. Rate-limit starts to at least 1.1 seconds apart by default; allow one navigation run at a time per backend process. The backend run deadline is 14 minutes and the client/proxy deadline is 15 minutes. Each request has bounded connect/read timeouts. Display OSRM/OpenStreetMap attribution below the map. Public-service requests send coordinates to the configured server; repeated large demos can point to a dedicated OSRM installation. No road request was run by the agent because verification belongs to the developer.

These choices implement the developer's explicit corrections: paths follow roads, individual bin points replace clusters, the stored demo fleet has 150 trucks, the table shows five rows per page, and the requested disclaimer and Aptarnauti count label are omitted.

### 4. Explicit workflow and stale-work protection

Use one workflow state union/reducer with `idle`, `predicting`, `bin_animation`, `predicted`, `routing`, `route_animation`, `completed`, `empty` and `error`, plus a failed-stage field where needed. A dedicated hook owns requests, a run token, abort controller and date lock; components render action, map, statuses and table.

On Start clear state/data sources while retaining map/camera, capture T, lock and call prediction. After setting predicted data, wait for the ready map to present its markers before starting navigation. Keep `predicted` as a real visual boundary rather than batching it away in the same render. Missing map configuration/load/render readiness is a stage error with finite feedback, not an infinite wait. Once navigation returns, hand routes to the drawing controller; only its completion for the current run transitions to `completed` and reveals a truck table paginated at five rows per page. Pagination resets for a new run and never changes map sources.

An empty prediction avoids navigation; an entirely unmappable due result has distinct feedback. Navigation failure retains selected markers. Any drawing error hides successful results and releases the lock. Restart reruns the full pipeline; no partial retry cache. Changing the date after a terminal result clears its markers/routes/table without launching work. Unmount aborts frontend requests, invalidates tokens and stops animation. Guard every async completion and lock release with the owning token.

### 5. Reuse MapLibre lifecycle and add focused animation support

After prediction, shuffle a separate array of eligible bin markers once per run with Fisher–Yates, preserving the prediction and navigation inputs. Reveal a growing prefix by adding batches of 1, 1, 1, 2, 2, 2, 4, 4, 4 and subsequent triplets of doubled batch sizes, capped at the mapped total. Wait for the existing map render acknowledgement for each prefix, then schedule the next appearance with a delay starting at 700 ms, multiplied by 0.88 per batch-size group and bounded below at 180 ms. This keeps early appearances perceptible while accelerating larger batches without adding DOM markers. Update the mapped count with each prefix and keep prediction feedback and date/start locks active. Each map update has a finite render deadline; cancellation clears both the reveal timer and existing animation/request resources. Reduced-motion mode presents all markers together. Only acknowledgement of the final marker set starts navigation.

Keep layer definitions stable outside changing run state. Reuse `AnalyticsMap` and its layer update mechanism; add narrowly scoped map readiness/error and render acknowledgement support with configurable accessible map labels, preserving Map Analytics defaults. Implement selected-bin and route layers separately. Reuse the existing point renderer with explicit clustering disabled for Demo. Preserve Map Analytics clustering defaults.

Animate GeoJSON LineString prefixes in MapLibre sources using `requestAnimationFrame`, cumulative segment distance and interpolation at the current progress distance. Convert API latitude/longitude to GeoJSON `[longitude, latitude]` only at the boundary. Animate routes simultaneously over approximately four seconds with stable restrained colors, place lines beneath individual selected-bin markers, and fit the useful extent once per run when needed. Single-coordinate routes can show a point instead of an invalid LineString.

Cancel frames on restart, failure, disposal and navigation. Report completion only when every route is fully presented; handle background-tab elapsed time and reduced-motion mode with a short deterministic reveal. A map-ready/render timeout prevents the table gate from remaining locked. Animated source updates avoid hundreds of React DOM elements. Avoid an unrelated second map implementation or broad shared-map refactor.

### 6. Road-following truck illustration

The shared `/admin/demo/truck/:truck_id` page checks the selected stored truck through the existing API, without displaying its name. Its title is `Šiukšliavežės sekimas`. Remove the page-local return and replay controls, descriptive disclaimer, completion/collection counter and color explanation as requested by the developer. Keep shared navbar navigation, loading/errors and road attribution.

`GET /demo/driving-route` resolves the fixed Vilnius illustration locations through the existing OSRM boundary, returning road geometry, ordered per-stop legs and snapped stop positions. The fixture is owned by `app.services.demo_driving`, avoiding an independent frontend coordinate path. Use the full continuous road overview for movement and the rendered line. Partition it into adjacent legs at vertices nearest the ordered snapped waypoints, sharing each boundary vertex. This avoids relying on exact equality between independent maneuver endpoints and introduces no straight connectors between bins. Reuse navigation's overlap guard, request pacing and explicit failure behavior. No straight-line fallback is available.

The frontend requests this route after validating the truck, then animates a single truck marker along each road leg using distance interpolation. Travel times vary by leg and distance, generally 6–14 seconds, with variable 1.8–3.4 second collection pauses. A monotonic eased progress function supplies acceleration, speed changes and deceleration. The camera follows the interpolated marker center at street zoom and holds the final position. Reduced-motion mode uses shorter movement and pauses. Collection changes point colors without exposing counters or completion controls.

The illustration remains independent of the selected truck's generated plan and introduces no GPS or operational collection writes. Request aborts, stale-response guards and frame/marker disposal protect navigation and unmount. The project date remains unlocked. Verification belongs to the developer.

## Risks / Trade-offs

- [Missing product and enriched sources] -> Require the delivered artifacts and explicit mounted paths before real verification; never replace them with a fake model or regenerate immutable history.
- [Registry/database mismatch] -> Validate identity coverage and fail with an actionable data-alignment error; disclose missing coordinates separately.
- [Long request or client departure] -> Fifteen-minute client/proxy deadline, honest loading, local cleanup and in-process overlap guard; backend work may continue after disconnect.
- [Road service unavailable] -> Use finite timeouts and explicit errors, without straight-line replacement geometry; retain selected markers for restart.
- [Map changes regress analytics] -> Extend existing lifecycle narrowly, retain defaults, and manually verify analytics layers/camera plus build/lint.
- [Provider lock persists accidentally] -> Persist only date, use owner-scoped cleanup, and manually exercise every terminal path and navigation.

## Migration Plan

No database migration. Supply the trusted product/input files and runtime versions; build the API image with portable source and inference dependencies; configure demo paths and proxy deadlines; then add frontend routes and shared date. Verify one real long run and repeatable failure cases. Rollback removes the demo routes/navigation/API additions and provider while retaining source data, model artifacts and all existing collection-plan records.
