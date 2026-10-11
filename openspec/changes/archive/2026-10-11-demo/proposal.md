# Proposal

## Why

VipTop needs a filmable end-to-end demonstration connecting its real fill predictor to bin selection, route visualization and a future driver experience. The application exposes map analytics and fleet management, but no screen presents this sequence.

## What Changes

- Add one application-wide, refresh-persisted project date with a navbar calendar restricted to September 2026. The selected day T is the predictor's input; predictions and routes are for T+1, including October 1 after September 30.
- Add `/admin/demo` with a prominent start action, large map, compact workflow status and assigned-truck table revealed only after route animation finishes.
- Expose the existing real CSV-backed predictor through the backend API, select fill levels 3 and 4, and resolve selected bin coordinates. Accept the existing roughly 4–5 minute inference wait without caching, retraining or performance work.
- Lock the global calendar and prevent another start throughout prediction, routing and route drawing; release the lock on completion, empty result, failure or leaving the page.
- Add deterministic assignments over up to 150 stored trucks and road-following OSRM paths, returning typed routes and explicit bin/stop assignments. Render individual bins without clustering and paginate truck results at five rows per page.
- Progressively draw routes with MapLibre, then allow truck rows to open `/admin/demo/truck/:truck_id`, a reusable hardcoded truck movement and bin collection demonstration.
- Handle empty prediction results, stage failures, restart and navigation cleanup without fabricated ML results or stuck loading states.

## Capabilities

### New Capabilities

- `project-date`: Shared September date selection, persistence, next-day context and run locking.
- `demo-planning`: Sequential prediction-to-road-routing workflow, map animation, results and lifecycle behavior.
- `truck-driving-demo`: Reusable illustrative driving and collection animation reached from assigned trucks.

### Modified Capabilities

- `daily-fill-prediction`: Add an application API for real next-day inference and service-bin selection while preserving the standalone model contract.
- `map-analytics`: Make the shared project date available without changing analytics calculations or agent behavior.

## Impact

Frontend App/provider, AdminLayout navigation, new demo pages/API clients, and existing reusable MapLibre lifecycle/layers; backend demo prediction/navigation interfaces and services, runtime configuration, dependency lock and Docker packaging. Extend `docs/data/fill-prediction.md` and `docs/development.md` with operational setup; update README feature/pipeline rows only where applicable. No database schema or route persistence is required. Existing collection-plan commands retain their explicitly synthetic provider; the demo does not invoke it or rebuild stored plans.

Material uncertainties: the trained product is not present at the configured path in this checkout; runtime dependencies must match its delivery metadata; the immutable ML registry and database bin IDs must align. These are prerequisites for live verification, not permission to generate substitute predictions. The long HTTP request needs a finite timeout comfortably above the accepted inference duration. Proposed defaults: initial date September 14, argmax fill levels 3/4 as due, and deterministic assignments with road geometry without carrier/capacity feasibility claims. GPS, authentication, confirmations, model changes and inference optimization remain out of scope.
