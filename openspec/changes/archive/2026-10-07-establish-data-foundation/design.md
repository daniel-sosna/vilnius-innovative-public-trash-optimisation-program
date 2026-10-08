# Design

## Context

See [proposal.md](proposal.md) for motivation and scope; project governance remains in [openspec/config.yaml](../../config.yaml). The new contracts are defined by [collection-records](specs/collection-records/spec.md) and [bin-synchronization](specs/bin-synchronization/spec.md).

The current backend consists of `app/main.py` constructing an otherwise empty FastAPI application. SQLAlchemy, psycopg, pydantic-settings, and Uvicorn are already dependencies, but there is no database setup, model metadata, or migration environment. The named application directories are placeholders rather than existing architectural layers that must all be populated.

Compose runs PostgreSQL 17 with persistent storage and waits for its health check before starting the backend. Both the backend Dockerfile and Compose currently launch Uvicorn directly; Compose also bind-mounts the backend directory and overrides its command. Migration integration must therefore cover both startup paths.

Live source investigation on 7 October 2026 retrieved 1,351 features matching the count query: 1,345 Polygons and six MultiPolygons. All selected IDs were distinct integers from 1 to 3,541, with usable coordinates and nonempty text addresses. Metadata advertises a 2,000-record limit, pagination and ordering support, `OBJECTID` as the object-ID field, nullable small-integer `KAIKS_NR`, and nullable text `ADRESAS`. Requests with a descriptive User-Agent and JSON Accept header succeeded; the initial default Python request received HTTP 403. These are investigation observations, not hard-coded dataset assertions.

Source: [layer metadata](https://opencity.idvilnius.lt/gis/rest/services/Miesto_tvark/Miesto_tvarkymas_public/MapServer/29?f=pjson).

## Goals / Non-Goals

**Goals:**

- Build one working path from normal backend startup through migration and live import to persistent, inspectable Bin rows.
- Keep record definitions and synchronization behavior reusable by later slices without introducing execution APIs now.
- Make failures visible and prevent a failed run from publishing partial registry updates.

**Non-Goals:**

- Filling every placeholder architectural directory, duplicating ORM records as separate domain objects, or creating generic repository/job frameworks.
- Spatial calculations beyond the agreed first-vertex mapping.
- Enforcing future prediction, route-execution, or service-recording policies. Refer to the proposal for excluded product features.

## Decisions

### 1. Use one SQLAlchemy model set and a focused database boundary

Place SQLAlchemy table mappings in `app/infrastructure/models.py`, engine/session setup in `app/infrastructure/database.py`, and settings in `app/core/config.py`. Use the existing synchronous SQLAlchemy/psycopg path. Each synchronization opens its own session; no session is shared across tasks or threads.

Alternatives: separate ORM/domain/DTO representations and a generic repository hierarchy would duplicate an otherwise small contract. A fully asynchronous database layer is unnecessary for this low-frequency job; offloading the synchronous workflow keeps periodic work off the event loop without introducing a second persistence approach.

### 2. Preserve the exact entity fields with database-enforced invariants

All columns are `NOT NULL` except `bins.address`. Internal IDs use `INTEGER GENERATED ALWAYS AS IDENTITY`; `bins.id` is an external `INTEGER` primary key with autoincrement explicitly disabled. Use PostgreSQL `INTEGER` rather than the source's narrower small-integer type to avoid an unnecessary bound on a shared external contract.

| Table | Columns | Additional constraints |
|---|---|---|
| `bins` | `id INTEGER PK`; `lat DOUBLE PRECISION`; `lon DOUBLE PRECISION`; `address TEXT NULL` | Latitude in [-90, 90], longitude in [-180, 180] |
| `trucks` | `id INTEGER identity PK`; `name TEXT`; `max_bins_per_trip INTEGER`; `available BOOLEAN` | Capacity > 0 |
| `routes` | `id INTEGER identity PK`; `service_date DATE`; `truck_id INTEGER FK`; `status TEXT` | Status in `PLANNED`, `IN_PROGRESS`, `COMPLETED`; database default `PLANNED` |
| `route_stops` | `id INTEGER identity PK`; `route_id INTEGER FK`; `bin_id INTEGER FK`; `stop_order INTEGER` | Stop order > 0; unique `(route_id, stop_order)` |
| `service_events` | `id INTEGER identity PK`; `bin_id INTEGER FK`; `service_ts TIMESTAMPTZ`; `fill_level TEXT`; `duration INTEGER`; `route_id INTEGER FK` | Duration >= 0; fill level in `EMPTY`, `LESS_THAN_HALF`, `MORE_THAN_HALF`, `FULL` |

Name check, unique, and foreign-key constraints consistently so errors and future migrations remain understandable. Geographic range checks also exclude infinities and PostgreSQL floating-point NaN; the source mapper independently checks finite numeric coordinates before persistence.

```text
Truck --< Route
            |
            +--< RouteStop    >-- Bin
            |
            +--< ServiceEvent >-- Bin
```

Every foreign key uses `ON DELETE RESTRICT` and retains stable referenced IDs. Do not configure ORM cascades that delete referenced records or null their relationships. This protects references; it is not a complete immutable-history system.

Do not add unique truck names, unique `(truck_id, service_date)`, unique `(route_id, bin_id)`, or unique event pairs. Those would introduce business restrictions not established by the current contract. Stop positions need not be contiguous at the database level. Capacity enforcement and the interpretation of truck availability belong to future routing, not triggers on these tables.

Alternatives: native PostgreSQL enums provide the same value restriction but make evolution more involved; text plus named checks is sufficient. Composite primary keys would conflict with the agreed identity contract. Audit fields, bin activation flags, coordinate history, PostGIS, and derived feature columns solve no requirement in this slice.

### 3. Index concrete relationships and chronological history

Add `routes(truck_id)`, `route_stops(bin_id)`, `service_events(route_id)`, and `service_events(bin_id, service_ts, id)`. The latter supports per-site history and latest-event retrieval with deterministic timestamp ties. The route-stop unique constraint already indexes `(route_id, stop_order)`; do not duplicate that index. Primary keys supply their own indexes.

Alternative: indexing every future filter, availability flag, status, date, or coordinate would precede an actual query requirement. Start with the required relationships and the explicitly identified historical access pattern.

### 4. Treat service timestamps as completion instants and retain raw observations

`service_ts` marks completion of emptying and the start of the next fill cycle; `fill_level` is observed immediately beforehand. Require callers to supply actual service timestamps, duration in whole seconds, capacity, and availability. Do not default observations to the current time or invent fill levels. Configure database sessions to use UTC. Planned `service_date` is a local Europe/Vilnius calendar date, with no constraint requiring all actual service timestamps to fall within that date.

The confirmed service unit is the whole site. This schema assumes a recorded service empties that unit completely; individual containers and partial collections are not separately modeled.

Future analytical code can order raw events by `(service_ts, id)` and pair consecutive events to derive elapsed intervals. The first event has no known preceding reset, and timestamp ties do not imply a positive interval. This change implements neither interval derivation nor training. GIS import supplies no service history, and no synthetic history is seeded.

Alternatives: naive timestamps would make elapsed intervals ambiguous across timezone changes; inserting derived intervals would couple storage to a future modeling approach. Historical site coordinates and immutable route assignments would need additional contracts and are deferred.

### 5. Run Alembic explicitly before Uvicorn, automated by normal container startup

Add Alembic, update `pyproject.toml` and `uv.lock`, and create `backend/alembic.ini`, the migration environment, and one initial revision. The migration environment uses the application's settings and model metadata. Alembic's own version table is migration bookkeeping, not an additional domain entity.

Add `backend/start.sh` as the backend image entrypoint. It runs `uv run alembic upgrade head`, stops on failure, and then replaces itself with the supplied server command using `exec`. The Dockerfile must copy the migration environment, configuration, and entrypoint into the image. Compose's command remains server arguments passed through that entrypoint; its existing database health dependency remains useful.

This preserves `docker compose up --build` as the standard local startup. Outside Docker, document the explicit migration command followed by Uvicorn. Development application reloads trigger another initial import but do not rerun migrations inside each application lifespan. CLI imports assume the schema has already been migrated.

Alternatives: `metadata.create_all` cannot version schema changes; database image initialization scripts do not update existing volumes. Running Alembic inside FastAPI lifespan couples DDL to worker/reload lifecycle. A separate migration service is unnecessary for this single-backend setup.

### 6. Use a small GIS client with real pagination and deterministic mapping

Implement the external boundary in `app/infrastructure/vilnius_gis.py`. Standard-library HTTP and JSON facilities are sufficient. Send a descriptive User-Agent such as `VipTop/0.1` and `Accept: application/json`, and use a finite request timeout. Do not reproduce browser cookies or add authentication.

Default query endpoint:

```text
https://opencity.idvilnius.lt/gis/rest/services/Miesto_tvark/Miesto_tvarkymas_public/MapServer/29/query
```

Send `where=1=1`, `outFields=KAIKS_NR,ADRESAS`, `returnGeometry=true`, `outSR=4326`, and `f=geojson`. Add `resultRecordCount=1000`, initially `resultOffset=0`, and `orderByFields=OBJECTID ASC`. The investigation verified pages containing 1,000 and 351 records, totaling the complete snapshot.

Accept continuation flags at either the collection top level or collection `properties`; continue if either reports `exceededTransferLimit=true`. Advance the offset by the requested page size, not the number returned, because ArcGIS can return short or empty intermediate pages. `OBJECTID` is a retrieval-order field only and is not stored. Fetch all pages before any upsert. Do not fetch daily metadata or hard-code the observed count as an invariant.

Validate each page as a JSON object with `type=FeatureCollection` and a features list; HTTP failures, JSON decoding errors, ArcGIS error payloads, or malformed collection shapes fail the run. Validate each feature minimally: a usable integer ID within PostgreSQL INTEGER bounds, a supported geometry, and a usable first coordinate. Reject booleans as IDs or coordinate numbers rather than accepting Python's bool-as-int behavior. No numeric-string or fractional-ID coercion is needed for the observed source.

```text
Polygon      coordinates[0][0]    --> [lon, lat]
MultiPolygon coordinates[0][0][0] --> [lon, lat]
```

Use the first two ordinates, checking finiteness and bounds. Skip unusable features with an identifier or page/feature position and reason. For missing, whitespace-only, or nontext addresses, map `address=None` and warn without skipping; otherwise retain the supplied text. If usable features duplicate an ID across the complete retrieval, fail the run before writing.

Alternatives: a single unpaged request works today but can silently omit future sites. Object-ID batch retrieval is another valid ArcGIS approach, but the source already supports a straightforward offset loop. Geometry libraries and centroid calculations are unnecessary and would depart from the agreed coordinate rule.

Reference: [ArcGIS query and pagination behavior](https://developers.arcgis.com/rest/services-reference/enterprise/query-map-service-layer/).

### 7. Publish only Bin upserts in one transaction

Implement one synchronous workflow in `app/services/bin_sync.py`: retrieve, map and validate the complete collection, then open a database transaction and perform PostgreSQL `INSERT ... ON CONFLICT (id) DO UPDATE`. Its update set contains only `lat`, `lon`, and `address`. Use modest upsert batches within the same transaction; a write failure rolls back the whole run. Fetching before the transaction avoids holding database resources during GIS requests.

Do not delete rows missing from the source, truncate tables, replace the registry, or modify any other entity. An empty/wholly unusable complete response produces no writes and a warning. Address `NULL` is authoritative for a usable feature and replaces a previously known address when the source now omits it.

Return/log counts for retrieved features, skipped unusable features, and committed upserted rows. Upserted includes valid rows whose values were already identical; it does not claim they were newly inserted or changed. Address warnings are separate from skipped-feature counts. Failures report their stage and reason and never report attempted writes as committed upserts.

Alternatives: delete-and-reinsert would break references; per-row or per-page commits could publish partial results after a later failure. Fetching and calculating separate inserted/updated/unchanged counts would add work without improving this slice's contract.

### 8. Own a sequential loop in FastAPI lifespan

Lifespan creates the application database resources, awaits one initial attempt via `asyncio.to_thread`, catches/logs synchronization exceptions, and then starts one asynchronous periodic loop. The loop waits for the interval after each attempt, executes the same synchronous workflow off the event loop, and continues after failures. The first wait follows the completed startup attempt, including a failed one.

Use a stop event that interrupts the interval wait. On shutdown, set the stop event, await the periodic task, and then dispose database resources. Do not cancel an await on a worker thread and assume that cancellation stopped its underlying HTTP/SQL work. An in-flight run must finish or fail and settle its transaction before disposal. Use finite database connection and synchronization statement/lock timeouts as well as the HTTP timeout so normal shutdown is not left waiting on unbounded I/O. Timeout choices are documented operational defaults, not new entity fields.

Support one backend worker with one timer. The loop cannot overlap its own startup/periodic attempts. Separate operator invocations are not coordinated with the timer; operators should wait for an automatic run to finish before issuing a manual run. No distributed lock or durable schedule is introduced. Process restarts trigger the initial attempt, and downtime does not cause replay of missed daily runs.

Settings use the existing pydantic-settings dependency:

| Setting | Default / purpose |
|---|---|
| `DATABASE_URL` | Existing Compose-provided connection setting |
| `BIN_SYNC_SOURCE_URL` | Layer 29 query endpoint; overridable for explicit manual verification |
| `BIN_SYNC_INTERVAL_SECONDS` | 86,400; positive value, shorten temporarily for manual periodic verification |
| `BIN_SYNC_HTTP_TIMEOUT_SECONDS` | 30; positive request timeout |

Migration failures stop startup; GIS/workflow failures are caught at the application boundary and do not. Invalid configuration is not treated as a recoverable GIS outage.

Alternatives: a job queue, cron deployment, or scheduler package adds infrastructure for one low-frequency job. HTTP-response BackgroundTasks do not own a recurring application lifecycle. Starting the first import without awaiting it would leave initial data readiness ambiguous relative to the agreed startup sequence.

### 9. Reuse the workflow in a manual command and document verification

Expose `uv run python -m app.interfaces.bin_sync` from the backend directory. It loads the same settings, owns its engine/session resources, invokes the same one-shot workflow, and returns zero for completion (including warned/skipped/no-data cases) or nonzero for failed retrieval/writing. It must not start the timer, create routes, or seed history.

Update README and `.env.example` during implementation with startup, migration, manual import, settings, the exact raw record semantics, and SQL inspection examples. Demonstrate the new slice through real PostgreSQL and the running backend. Use a separate disposable verification database for explicitly synthetic truck/route/event records and controlled GIS fixture responses; these are verification inputs, not observed operational history. No operational write/read endpoint is needed to prove this slice.

Verification covers repeated imports, mapping for both geometries, constraints, joined truck attribution and ordered history, missing/invalid/absent source features, duplicate IDs, later-page and transaction failures, periodic behavior with a shortened interval, request responsiveness, and graceful shutdown. Document manual procedures and the reusable operator command rather than adding an automated test suite or test framework.

Alternative: adding CRUD or a frontend solely to inspect this change would expand the slice beyond the requested foundation.

## Risks / Trade-offs

- [External IDs could be reassigned or recycled] -> Record stable identity as an assumption; the snapshot proves uniqueness only at the time fetched. Do not silently change IDs or add a second identity scheme.
- [Absent sites remain future prediction candidates] -> Retain them as required and disclose that the current schema cannot distinguish source retirement; revisit only with a real activation requirement.
- [First polygon vertex may not be a road-access point] -> Preserve the agreed deterministic rule; future routing integration must assess access/snapping without adding speculative location fields now.
- [Current site attributes may differ from those at historical service time] -> Document that historical joins use current attributes; no location snapshots are promised.
- [Reassigning a Route can change the truck derived for existing events] -> Future execution writers must address assignment changes once servicing starts; this change supplies relationships but no reassignment API or trigger.
- [Event bin/route references do not prove membership in RouteStop] -> Planned stops and actual service facts remain separate. The later event-recording slice must decide how to handle unplanned collections.
- [Public access and response shape can change] -> Identify requests, use timeouts, validate collection envelopes, log errors, and retain the last committed registry. Do not add a parallel fallback source.
- [Pagination is ordered but not a transactional upstream snapshot] -> Reject duplicate usable IDs and keep local publication atomic; source changes during retrieval can still affect completeness. No upstream snapshot guarantee is claimed.
- [In-process timer duplicates under multiple workers, replicas, or concurrent manual imports] -> Document single-worker scheduling and operator sequencing; revisit ownership before changing deployment topology.
- [Startup import delays readiness and graceful shutdown waits for a running import] -> Keep requests and database operations bounded; accept this trade-off for deterministic startup and safe resource cleanup.

## Migration Plan

1. Ship the models, Alembic dependency/lock update, migration files, entrypoint, synchronization workflow, and lifecycle wiring in the same implementation change.
2. Apply the initial migration in dependency order: bins and trucks, routes, then route stops and service events, with named constraints and justified indexes. Schema creation is transactional and creates no seed records.
3. Validate against a disposable empty database, then repeat `upgrade head` and normal startup against populated storage to confirm preservation. Verify the standalone image as well as the Compose bind-mounted startup path.
4. Normal container startup migrates and launches Uvicorn; lifespan attempts import. A GIS failure leaves the migrated schema usable with the prior registry, or an empty registry on first launch, and a later attempt remains scheduled.
5. A failed initial migration prevents server launch. Correct the migration/configuration before restarting rather than using runtime schema creation as a fallback.
6. Ordinary code rollback can leave these additive tables intact. A deliberate downgrade to the baseline drops the five tables in reverse dependency order and destroys their data; exercise that only on disposable storage or after explicitly preserving required data. Never downgrade or clear tables automatically after a synchronization failure.

## Open Questions

There are no unresolved decisions blocking this change. Site-level fill-reporting conventions (including exactly-half observations), restrictions on route reassignment after service, and planned-stop membership for actual servicing are deferred to the event-recording slice; they do not change this foundation's fields or synchronization contract.
