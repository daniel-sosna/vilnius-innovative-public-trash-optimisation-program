# Proposal

## Why

VipTop currently has no persistent collection records or imported collection sites. Establishing these records and a reliable live GIS import gives the next prediction and driver-workflow changes a shared data foundation without implementing those capabilities prematurely.

## What Changes

- Establish PostgreSQL storage for exactly five domain entities: Bin, Truck, Route, RouteStop, and ServiceEvent, using the fields agreed during exploration.
- Treat one Vilnius collection site as one Bin and one service unit; truck trip capacity counts sites.
- Preserve external `KAIKS_NR` identifiers for bins and generate independent primary keys for the other entities. Require every entity relationship and preserve referenced history.
- Store ordered route stops, per-day routes assigned to trucks, and observed pre-emptying fill levels with service completion timestamps and durations in seconds. Keep truck attribution on Route rather than duplicating it in ServiceEvent.
- Establish versioned migrations that complete before the backend server starts.
- Synchronize bins from the Vilnius public GIS source on application startup and approximately every 24 hours, handling both Polygon and MultiPolygon responses and fetching every page.
- Insert new bins and update coordinates and addresses by external ID. Retain absent bins, skip unusable features with diagnostics, and preserve existing data when a synchronization fails.
- Provide one repeatable synchronization command, useful summaries and exit codes, and documented verification through the running PostgreSQL/backend environment.

Prediction, training, prioritisation, route generation, road-matrix integration, optimisation, navigation, frontend changes, operational CRUD endpoints, synthetic-history generation, and extra domain fields are outside this change. Route and ServiceEvent storage does not imply implementing their future execution workflows.

## Capabilities

### New Capabilities

- `collection-records`: Persist collection sites, truck capacities and availability, assigned daily routes, ordered stops, and raw service observations with required relationships and protected history.
- `bin-synchronization`: Automatically maintain the collection-site registry from public GIS data with complete retrieval, stable-identity updates, diagnostics, and failure isolation.

### Modified Capabilities

None. The project has no existing capability specs.

## Impact

- Backend database configuration, SQLAlchemy models, GIS integration, synchronization service, and FastAPI lifecycle wiring.
- Alembic dependency, migration configuration and initial revision; backend dependency lockfile updates during implementation.
- Backend container startup and Compose integration so migrations precede Uvicorn without adding a deployment solely for synchronization.
- Documented shared record contracts for future backend, data/ML, and optimisation consumers. No existing API is replaced.
- Local run documentation and a manual synchronization command. Project-wide governance remains in `openspec/config.yaml`.

### Assumptions and remaining uncertainties

- The team confirmed that a whole collection site is one service unit. A ServiceEvent assumes that this modeled unit was emptied completely.
- `KAIKS_NR` is assumed to remain stable and not be recycled. On 7 October 2026, live investigation found 1,351 distinct integer identifiers, but this does not establish long-term identity guarantees.
- That snapshot contained 1,345 Polygons and six MultiPolygons, no missing addresses, and usable first coordinates. The source permits missing addresses; this proposal stores them as `NULL` rather than inventing values.
- One backend worker owns the periodic timer. Multiworker or replicated scheduling is deferred.
- Removed sites remain stored and cannot yet be distinguished from currently listed sites. Historical events resolve current site attributes, rather than historical coordinate/address snapshots.
- Site-level fill-reporting conventions, route reassignment restrictions after servicing, and whether actual servicing must match a planned stop belong to later execution changes.
