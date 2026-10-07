# VipTop Waste Collection Optimisation

VipTop MVP for exploring more efficient public waste-container collection in Vilnius. The backend stores collection records and automatically synchronizes collection sites from public GIS data. Prediction, route generation, and driver interfaces are future changes.

## Technologies

- React, TypeScript, Vite, Tailwind CSS, and shadcn/ui
- Python 3.12, FastAPI, Uvicorn, SQLAlchemy, psycopg, Alembic, and pydantic-settings
- PostgreSQL
- Docker Compose

## Project structure

```text
.
├── frontend/                # React web application
├── backend/
│   ├── alembic/            # Reviewed database migrations
│   ├── alembic.ini
│   ├── start.sh            # Migrate before starting the server
│   └── app/
│       ├── core/           # Configuration and shared setup
│       ├── domain/         # Business concepts and rules
│       ├── repositories/   # Data-access abstractions
│       ├── services/       # Reusable application services
│       ├── use_cases/      # Application workflows
│       ├── interfaces/     # API-facing layer
│       ├── infrastructure/ # Database and external integrations
│       ├── ml/             # Future prediction logic
│       ├── optimization/   # Future route optimisation logic
│       └── main.py
├── scripts/                 # Future database and utility scripts
├── docs/                    # Repeatable manual verification
└── docker-compose.yml
```

## Run locally

Docker and Docker Compose are the only prerequisites. Start the complete development environment with:

```bash
docker compose up --build
```

The services are available at:

- Frontend: <http://localhost:5173>
- Backend: <http://localhost:8000>
- FastAPI docs: <http://localhost:8000/docs>

Copy `.env.example` to `.env` only if you want to override the local development defaults.

The backend entrypoint runs `alembic upgrade head` before Uvicorn. Migration failure prevents server startup. FastAPI then attempts an initial GIS import before serving requests. Import failure is logged and the backend starts with its stored registry (which is empty on a first failed import). The application attempts another import approximately 24 hours after each attempt completes, including failures. Development reloads trigger an initial import again, but migrations run in the container entrypoint rather than the application lifecycle.

To run the backend outside Docker, install [uv](https://docs.astral.sh/uv/), provide an accessible PostgreSQL database, and run from `backend/`:

```bash
export DATABASE_URL=postgresql+psycopg://viptop:viptop@localhost:5432/viptop
uv sync --locked
uv run alembic upgrade head
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

These credentials are the local Compose defaults; use the connection details for your database. Application settings are read from environment variables. Compose reads the root `.env`; the standalone commands require exported variables.

## Collection records

One Bin represents a whole collection site, not an individual physical container. Truck capacity counts sites per trip. Only the following domain fields are stored:

| Table | Fields |
|---|---|
| `bins` | `id`, `lat`, `lon`, `address` |
| `trucks` | `id`, `name`, `max_bins_per_trip`, `available` |
| `routes` | `id`, `service_date`, `truck_id`, `status` |
| `route_stops` | `id`, `route_id`, `bin_id`, `stop_order` |
| `service_events` | `id`, `bin_id`, `service_ts`, `fill_level`, `duration`, `route_id` |

`bins.id` is the external integer `KAIKS_NR`, with no generator. The other IDs are independently generated PostgreSQL identities. All values and foreign keys are required except `bins.address`, which can be `NULL`. Referenced bins, trucks, and routes cannot be deleted. `alembic_version` is migration bookkeeping.

Routes are assigned work for a particular Europe/Vilnius service date. Status defaults to `PLANNED` and accepts `PLANNED`, `IN_PROGRESS`, or `COMPLETED`. A truck can have multiple routes on one date. `available` is explicitly supplied and will later control routing participation; `max_bins_per_trip` must be positive. Stops use positive, one-based positions unique within their route. The database does not require contiguous positions or prevent a repeated bin at another position.

A ServiceEvent records complete emptying of the modeled site. Its timezone-aware `service_ts` is the completion instant and starts the next fill cycle. `fill_level` is observed immediately before emptying and accepts `EMPTY`, `LESS_THAN_HALF`, `MORE_THAN_HALF`, or `FULL`. `duration` is a nonnegative integer in seconds. Database sessions use UTC. Actual servicing can cross midnight relative to the planned service date.

The truck is derived through the event's route. Raw history supports deriving intervals and ML features later, but none are persisted. The first event has no known previous reset; timestamp ties do not imply a positive interval. GIS import does not create service history, trucks, routes, or stops. Synthetic verification data must be kept in disposable storage, separate from observed operational records.

The foundation does not enforce planned-stop membership for an actual service or prevent truck reassignment on a route. Those policies, site-level fill-reporting conventions, and partial collections belong to later execution changes. Historical events see the bin's current address/coordinates; historical location snapshots are not stored.

Open a database console with the default Compose credentials:

```bash
docker compose exec db psql -U viptop -d viptop
```

Useful inspection queries:

```sql
SELECT count(*) AS stored_sites FROM bins;
SELECT id, lat, lon, address FROM bins ORDER BY id LIMIT 10;

-- Ordered stops for a route; replace the route ID as appropriate.
SELECT stop_order, bin_id FROM route_stops
WHERE route_id = 15 ORDER BY stop_order;

-- Raw chronological history and truck attribution.
SELECT e.id, e.bin_id, e.service_ts, e.fill_level, e.duration,
       e.route_id, r.truck_id, t.name
FROM service_events AS e
JOIN routes AS r ON r.id = e.route_id
JOIN trucks AS t ON t.id = r.truck_id
WHERE e.bin_id = 634 ORDER BY e.service_ts, e.id;
```

## Bin synchronization

The source is [Vilnius GIS collection sites, layer 29](https://opencity.idvilnius.lt/gis/rest/services/Miesto_tvark/Miesto_tvarkymas_public/MapServer/29). Every run fetches all GeoJSON pages in output reference 4326. Polygon uses `coordinates[0][0]`; MultiPolygon uses `coordinates[0][0][0]`. Both supply `[longitude, latitude]`. The first vertex is a representative location, not a promised road entrance.

Valid sites are inserted or updated by `KAIKS_NR` in one transaction. Only `lat`, `lon`, and `address` change on an existing Bin. Missing, blank, or nontext source addresses become `NULL`, replacing any previous address. Invalid IDs/geometries are skipped with warnings; duplicate usable IDs fail the whole run. Absent sites remain untouched. Failures, empty collections, and wholly unusable collections never clear the registry. No fallback sites or history are fabricated.

Run a single import after schema initialization, waiting for any automatic import to finish first:

```bash
docker compose exec backend uv run python -m app.interfaces.bin_sync
```

Outside Docker, run `uv run python -m app.interfaces.bin_sync` from `backend/` with `DATABASE_URL` exported. The command shares the automatic import workflow and does not launch the timer. It returns zero for a completed run, including warned/skipped/no-data cases, and nonzero for failure. Summaries report retrieved, skipped, and committed upserted counts. Upserted includes rows already holding identical values; address warnings do not count as skipped features.

| Environment setting | Default |
|---|---|
| `DATABASE_URL` | Compose PostgreSQL connection using `postgresql+psycopg` |
| `BIN_SYNC_SOURCE_URL` | Layer 29 `/query` endpoint |
| `BIN_SYNC_INTERVAL_SECONDS` | `86400` (positive seconds after the last attempt completes) |
| `BIN_SYNC_HTTP_TIMEOUT_SECONDS` | `30` (positive seconds for socket I/O inactivity) |

Database connection timeout is 10 seconds; each synchronization transaction uses a 30-second statement timeout and a 5-second lock timeout. HTTP timeout applies to socket operations, not an overall deadline for a whole multi-page import. Startup readiness and graceful shutdown may wait for the current import to settle. Shutdown interrupts an interval wait immediately and waits for in-flight work before releasing the database engine.

Run one backend worker/replica: its application lifecycle owns one sequential timer. Manual runs are not coordinated with that timer. Restarts import again and do not replay missed daily jobs. External ID stability is assumed. Retained sites absent from the current source cannot be distinguished from currently listed sites until a later activation requirement is introduced.

## Migration and verification

From `backend/`, with `DATABASE_URL` exported:

```bash
uv run alembic upgrade head
uv run alembic check
```

Repeated upgrades preserve records. Later schema changes need reviewed Alembic revisions. Ordinary code rollback can retain these additive tables. An explicit `uv run alembic downgrade base` destroys all five tables and their records; use it only on disposable verification storage or after preserving required data. Import failure never triggers a downgrade.

Follow [the manual data-foundation verification procedure](docs/data-foundation-verification.md) for synthetic SQL records, controlled GIS responses, rollback checks, and lifecycle/container verification.
