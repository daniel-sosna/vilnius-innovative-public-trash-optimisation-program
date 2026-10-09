# VipTop Waste Collection Optimisation

VipTop MVP for exploring more efficient public waste-container collection in Vilnius. Administrators can manage the truck fleet through the Lithuanian UI and persistent API. The backend also stores collection records and imports collection sites from public GIS data on explicit command invocation. Prediction, route generation, and driver interfaces are future changes.

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
│       ├── interfaces/     # trucks/ HTTP API and bin_sync/ CLI
│       ├── infrastructure/ # Database engine and ORM persistence
│       ├── integrations/   # Third-party clients and source mapping
│       ├── ml/             # Future prediction logic
│       ├── optimization/   # Future route optimisation logic
│       └── main.py
├── scripts/                 # Future database and utility scripts
├── docs/                    # Repeatable manual verification
└── docker-compose.yml
```

## Run locally

Docker and Docker Compose are the only prerequisites. From the repository root, create `.env` if it does not already exist, then start the complete development environment:

```bash
test -f .env || cp .env.example .env
docker compose up --build -d
```

The services are available at:

- Frontend: <http://localhost:5173>
- Backend: <http://localhost:8000>
- FastAPI docs: <http://localhost:8000/docs>

`BIN_SYNC_SOURCE_URL` and `BIN_SYNC_HTTP_TIMEOUT_SECONDS` are required alongside the connection. For an existing `.env`, add any missing settings and update the source URL to the full all-attributes query in `.env.example`, preserving your connection details. Remove the obsolete synchronization interval line; leftover unrelated keys are ignored. Equivalent exported environment variables also work.

The backend entrypoint runs `alembic upgrade head` before Uvicorn. Migration failure prevents server startup. Startup, restart, development reload, and idle runtime make no GIS requests. The registry remains empty or holds its last imported values until an operator explicitly imports sites. There is no background synchronization task or import-related shutdown wait.

After the services are running, populate Bins once:

```bash
docker compose exec backend uv run python -m app.interfaces.bin_sync
```

This command imports the complete registry and exits. Run it again explicitly when a refresh is needed.

To run the backend outside Docker, install [uv](https://docs.astral.sh/uv/), provide an accessible PostgreSQL database, and run from `backend/`:

```bash
export DATABASE_URL=postgresql+psycopg://viptop:viptop@localhost:5432/viptop
uv sync --locked
uv run alembic upgrade head
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

After the native server is running, open another terminal in `backend/` and import once using the same accessible connection:

```bash
export DATABASE_URL=postgresql+psycopg://viptop:viptop@localhost:5432/viptop
uv run python -m app.interfaces.bin_sync
```

These credentials are the local Compose defaults; use the connection details for your database. Native commands, including Alembic and the importer, load the repository-root `.env` using the configuration module's location, independent of the working directory. The shared file can include `POSTGRES_*` settings. Exported variables override dotenv values: the localhost connection above overrides the example's container-only `db` hostname. No exported synchronization variables are needed when the file contains them. Standalone images obtain all required settings from their environment and do not need a copied or mounted dotenv file.

## Truck management

Open `/` and choose `Administratorius` to enter `/admin/trucks`. `Vairuotojas` is a disabled placeholder. Admin access requires no authentication. The shared navbar links to `Šiukšliavežės`; below 640 pixels, links collapse into a hamburger menu. Its labeled toggle supports keyboard opening, selection closes the menu, and Escape closes it and returns focus to the toggle.

The screen supports name search, availability and inclusive site-capacity filters, with at most 10 trucks per page, previous/next controls and a page-number input submitted with Enter or `Eiti`. Filter changes reset to page 1. The always-visible, right-aligned action row above the table contains equally sized `Pridėti šiukšliavežę` then the filled `Išvalyti filtrus` button. The add button opens the same form used for editing a row; new forms default to available. Capacity counts collection sites, not individual containers. Delete requires confirmation and retains the database row/history. Successful CRUD refreshes the whole-fleet overview and current filtered page, recovering to the last valid page if needed, without a full page reload.

Create/edit success appears as `Šiukšliavežė išsaugota.` in a toast entering from the top right; failed save requests show an error toast while preserving entered values. Field validation stays beside inputs. Toasts support accessible announcements, labeled dismissal, reduced motion and automatic dismissal, and remain visible above open dialogs. Read refresh failures retain their own retry controls; retrying does not repeat a committed save or its toast.

| API | Behaviour |
|---|---|
| `GET /trucks` | Nondeleted page; optional `name`, `available`, `min_max_bins_per_trip`, `max_max_bins_per_trip`, `page` |
| `GET /trucks/stats` | Whole nondeleted fleet: `total`, `available_count`, `average_max_bins_per_trip` |
| `GET /trucks/{id}` | Nondeleted detail, or `404` |
| `POST /trucks` | Required `name`, `max_bins_per_trip`, `available`; `201` saved truck |
| `PATCH /trucks/{id}` | Partial updates to those three fields; `200` saved truck; missing/deleted ID is `404` |
| `DELETE /trucks/{id}` | Atomic soft deletion; bodyless `204`; missing/already deleted ID is `404` |

List responses use `{ "items": [...], "total": 21, "page": 1, "page_size": 10 }`. Pages are one-based and default to 1; invalid/nonpositive pages return `422`, while a valid page beyond the results returns empty items with the matching total. Count and items apply the same filters before pagination, ordered by ID. Invalid UI page jumps show a Lithuanian error without fetching; changing/clearing filters resets both the page and page input. Names use trimmed, case-insensitive literal substring matching; filters combine with AND. Blank search has no effect. Capacity bounds must be integers 1–99 with minimum no greater than maximum.

The overview above the filters covers all nondeleted trucks independently of table filters/pages: total, average maximum site capacity (one decimal in Lithuanian formatting), and available percentage with a proportional green circular arc. `GET /trucks/stats` returns `{ "total": 21, "available_count": 11, "average_max_bins_per_trip": 11.0 }` for the synthetic 1–21-capacity example. The average is null for an empty fleet, displayed as — alongside 0 total and 0% availability. Statistics have independent loading/error/retry states; a failed refresh does not undo or repeat a committed mutation.

The screen uses a wider aligned admin layout, neutral gray surfaces and leaf branding. The available/total count beneath `Prieinamos šiukšliavežės` (for example, `24 iš 27`) matches the size and weight of the other overview values; the circular percentage remains beside it or wraps at narrow widths. The capacity column is `Max Aikštelių per reisą`. Truck-specific frontend files live under `frontend/src/pages/trucks/`; shared layout/branding/UI primitives, toast provider and `TablePagination` live under `components/`. Backend HTTP router/schemas live under `app/interfaces/trucks/`; the CLI lives under `app/interfaces/bin_sync/` and keeps the existing `python -m app.interfaces.bin_sync` invocation.

Truck responses expose `id`, `name`, `max_bins_per_trip`, `available`, `deleted`. Mutation inputs trim nonempty names, require integer capacity 1–99 and boolean availability, reject explicit nulls and unknown fields, and permit duplicate names. `id`/`deleted` cannot be set by clients. Omitted PATCH fields remain unchanged; an empty patch returns the eligible unchanged truck. Validation errors return `422`; persistence failures return generic `500` responses without partial changes.

The browser calls same-origin `/api/trucks`; Vite strips `/api` and proxies to FastAPI. Compose configures server-only `VIPTOP_API_PROXY_TARGET=http://backend:8000`. For native frontend development, the default is `http://127.0.0.1:8000`; override it for a different backend port:

```bash
cd frontend
npm ci
VIPTOP_API_PROXY_TARGET=http://127.0.0.1:8000 npm run dev
```

`npm run build` builds the frontend, and `VIPTOP_API_PROXY_TARGET=http://127.0.0.1:8000 npm run preview` serves the build with the same proxy. Deep-link open/refresh is supported in development and preview. A future production static host will need an equivalent API proxy and SPA fallback.

## Collection records

One Bin represents a whole collection site, not an individual physical container. Truck capacity counts sites per trip. Only the following domain fields are stored:

| Table | Fields |
|---|---|
| `bins` | `id`, `lat`, `lon`, `address`, `type`, `greening` |
| `trucks` | `id`, `name`, `max_bins_per_trip`, `available`, `deleted` |
| `routes` | `id`, `service_date`, `truck_id`, `status` |
| `route_stops` | `id`, `route_id`, `bin_id`, `stop_order` |
| `service_events` | `id`, `bin_id`, `service_ts`, `fill_level`, `duration`, `route_id` |

`bins.id` is the external integer `KAIKS_NR`, with no generator. The other IDs are independently generated PostgreSQL identities. All values and foreign keys are required except `bins.address`, `bins.type`, and `bins.greening`, which can be `NULL`. Type and greening are unrestricted text: the database accepts labels outside the known GIS mappings. Referenced bins, trucks, and routes cannot be deleted. `alembic_version` is migration bookkeeping.

Routes are assigned work for a particular Europe/Vilnius service date. Status defaults to `PLANNED` and accepts `PLANNED`, `IN_PROGRESS`, or `COMPLETED`. A truck can have multiple routes on one date. Truck names must be nonblank and `max_bins_per_trip` counts collection sites, with integer capacity 1–99. `available` is explicitly supplied and will later control routing participation. `deleted` defaults to false; retiring a truck sets deleted true and available false, retaining the row and its historical references. Future route generation must require both nondeleted and available trucks; historical route queries join retained trucks regardless of retirement. Stops use positive, one-based positions unique within their route. The database does not require contiguous positions or prevent a repeated bin at another position.

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
SELECT id, lat, lon, address, type, greening FROM bins ORDER BY id LIMIT 10;
SELECT type, greening, count(*) FROM bins GROUP BY type, greening;

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

The configured query is retained, including `outFields=*`, the example's 50-record page size, and spatial relation. The client starts at offset zero and uses stable `OBJECTID ASC` ordering. It advances by the requested page size while either continuation flag indicates more data, even after short or empty pages. Supported page sizes are integers from 1 to 1,000; unsupported sizes fail without publishing changes. Bare query URLs retain a 1,000-record default for controlled inputs.

Valid sites are inserted or updated by `KAIKS_NR` in one transaction. Only `lat`, `lon`, `address`, `type`, and `greening` change on an existing Bin. `TIPAS` uses the exact ten-code type mapping documented in the [manual verification procedure](docs/data-foundation-verification.md); `ZELDINIMAS` maps 1 to `Taip`, 2 to `Ne`, and 3 to `Taip, agentūrai ES pritarus`. Missing/null metadata becomes `NULL` silently. Unknown or unusable non-null codes become `NULL` with a warning identifying the site, field, and raw value; the valid site is still imported. Boolean, float, and text codes are not coerced. GIS is authoritative, so later imports can clear metadata or overwrite manually entered free text.

Missing, blank, or nontext source addresses become `NULL`, replacing any previous address. Invalid IDs/geometries are skipped with warnings; duplicate usable IDs fail the whole run. Absent or skipped sites retain every stored value. Failures, empty collections, and wholly unusable collections never clear the registry. No fallback sites or history are fabricated.

Run a single import after schema initialization:

```bash
docker compose exec backend uv run python -m app.interfaces.bin_sync
```

Outside Docker, run `uv run python -m app.interfaces.bin_sync` from `backend/` with the accessible `DATABASE_URL` exported and sync settings in the root `.env`. The command runs the reusable import workflow once without starting a server or scheduling another run. It returns zero for a completed run, including warned/skipped/no-data cases, and nonzero for failure. Summaries report retrieved, skipped, and committed upserted counts. Upserted includes rows already holding identical values; address and optional metadata warnings do not count as skipped features.

| Environment setting | Configuration |
|---|---|
| `DATABASE_URL` | Compose PostgreSQL connection using `postgresql+psycopg` |
| `BIN_SYNC_SOURCE_URL` | Required; full layer 29 query in `.env.example`, selecting all attributes and 50 records per page |
| `BIN_SYNC_HTTP_TIMEOUT_SECONDS` | Required; example `30` (positive finite seconds for socket I/O inactivity) |

Database connection timeout is 10 seconds; each synchronization transaction uses a 30-second statement timeout and a 5-second lock timeout. HTTP timeout applies to socket operations, not an overall deadline for a whole multi-page import. These limits apply to the explicit importer, which owns and disposes its database engine on success or failure. Application readiness and shutdown do not wait for GIS work in a separately launched import process.

Importing is operator-controlled. A source change alone does not refresh stored values, and application restarts preserve them. Avoid simultaneous manual imports; commands are not coordinated with one another. External ID stability is assumed. Retained sites absent from the current source cannot be distinguished from currently listed sites until a later activation requirement is introduced.

## Migration and verification

From `backend/`, with `DATABASE_URL` exported:

```bash
uv run alembic upgrade head
uv run alembic check
```

Repeated upgrades preserve records. Revision `0002` adds only nullable `type` and `greening` columns; existing rows start with null metadata and all original records survive. Apply migrations before running the updated importer. Rebuild the backend with `docker compose up --build` to package the revision; its entrypoint upgrades automatically. Native operators run the explicit command above with all required settings available from dotenv/environment, including the source URL and HTTP timeout. Alembic uses the shared Settings class, but migrations perform no GIS I/O.

Later schema changes need reviewed Alembic revisions. Ordinary code rollback can retain additive columns. An explicit `uv run alembic downgrade 0001` drops only the two metadata columns and loses their values; original records and references remain. Downgrade to `base` destroys all five tables and their records. Exercise downgrades only on disposable verification storage or after preserving required data. Import failure never triggers a downgrade.

Revision `0003` adds truck retirement and enforces nonblank names, capacity 1–99 and deleted/unavailable consistency. Existing valid truck values and all historical references are preserved. Incompatible existing names/capacities cause migration failure with truck IDs and reasons; no values are silently corrected. Downgrade to `0002` refuses while retired trucks exist so an old application cannot accidentally display them. Keep the newer application/schema when retirement data exists.

Follow [the manual data-foundation verification procedure](docs/data-foundation-verification.md) for synthetic SQL records, controlled GIS responses, rollback checks, and lifecycle/container verification.

Follow [the truck-management verification procedure](docs/truck-management-verification.md) for truck migration, API and browser verification on disposable storage.
