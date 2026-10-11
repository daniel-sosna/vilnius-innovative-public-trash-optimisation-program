# Development

How to configure and run the stack beyond the [Quick Start](../README.md#quick-start).

## Docker Compose stack

| Service | Default URL |
|---|---|
| Frontend (Vite dev server) | <http://localhost:5173> |
| Backend (FastAPI) | <http://localhost:8000>, API reference at `/docs` |
| PostgreSQL 17 | `localhost:5432`, user/database `viptop` |

- `backend/` and `frontend/` are mounted into their containers, so code changes reload automatically.
- On every start the backend runs `alembic upgrade head` before Uvicorn. If a migration fails, the backend does not start. Startup never imports or syncs data.
- `docker compose down --volumes` deletes the database and the dependency volumes. Files in the data directory are kept.
- After dependencies change, rebuild the images and refresh the frontend's `node_modules` volume:

  ```bash
  docker compose build backend frontend
  docker compose run --rm --no-deps frontend npm ci
  docker compose up -d
  ```

## Configuration

Settings come from the repository-root `.env`, which is created from `.env.example`. Exported environment variables override it. Native backend commands, including Alembic and the CLIs, read the root `.env` whatever the working directory. Unknown settings are ignored.

| Variable | Meaning |
|---|---|
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Database created by the `db` container |
| `DATABASE_URL` | Required. A `postgresql+psycopg://` connection. The example value uses the container hostname `db`. |
| `VASA_TILE_URL_TEMPLATE`, `VASA_BIN_URL_TEMPLATE`, `VASA_HISTORY_URL_TEMPLATE`, `VASA_SCHEDULE_URL_TEMPLATE` | HTTPS endpoints for [bin sync](data/bin-sync.md) and [schedule sync](data/bin-schedule-sync.md) |
| `BIN_SYNC_HTTP_TIMEOUT_SECONDS` | Required. Positive socket timeout for VASA requests. |
| `VITE_MAP_STYLE_URL` | MapLibre style for every map. There is no fallback in the code. The style must provide the `Noto Sans Regular` font used for cluster counts. |
| `VIPTOP_DATA_DIR` | Host folder with the CSV exports and GeoJSON sources, mounted as the backend's `/app/data`. The default is `backend/data/`. See [Data directory](#data-directory). |
| `COMPOSE_FILE`, `FRONTEND_PORT`, `BACKEND_PORT`, `DB_PORT` | See [Several worktrees at once](#several-worktrees-at-once) |

## Data directory

CSV exports and GeoJSON sources (population density, district boundaries, service zones) live in `backend/data/`, which git and the Docker build ignore. To use another folder, set `VIPTOP_DATA_DIR`. A relative value is resolved from the repository root.

- Create the folder before starting the stack. If it doesn't exist, Docker creates it empty and owned by root, and the import then finds nothing.
- After changing the variable, run `docker compose up -d` to recreate the backend.
- `scripts/dev-info.sh` prints the folder in use.

## Native backend

This needs [uv](https://docs.astral.sh/uv/), Python 3.12 and a reachable PostgreSQL. Run from `backend/`:

```bash
export DATABASE_URL=postgresql+psycopg://viptop:viptop@localhost:5432/viptop
uv sync --locked
uv run alembic upgrade head
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The exported `DATABASE_URL` overrides the `db` hostname from `.env`. Every CLI under `app.interfaces` runs the same way: `uv run python -m app.interfaces.<module>`. In Docker, prefix it with `docker compose exec backend`.

`uv run alembic check` confirms that the models match the migrations. Downgrades are not a supported way to go back. Restore a backup, or recreate the database with `docker compose down --volumes`.

## Native frontend

Run from `frontend/`:

```bash
test -f .env.local || cp .env.example .env.local   # sets VITE_MAP_STYLE_URL
npm ci
VIPTOP_API_PROXY_TARGET=http://127.0.0.1:8000 npm run dev
```

- The browser calls same-origin `/api/...`. Vite strips `/api` and proxies the request to `VIPTOP_API_PROXY_TARGET`, which defaults to `http://127.0.0.1:8000`. Compose sets it to `http://backend:8000`.
- `npm run build` embeds `VITE_MAP_STYLE_URL` at build time. `npm run preview` serves the build with the same proxy.
- Deep links work in both dev and preview. A static production host would need the same `/api` proxy and an SPA fallback.
- `npm run lint` runs ESLint.

## Several worktrees at once

Every checkout gets its own Compose project, containers, network and volumes, so only the host ports clash. To run several checkouts side by side, turn on **worktree mode** in each checkout's `.env`:

```bash
COMPOSE_FILE=docker-compose.yml:docker-compose.worktree.yml
```

`docker compose up --build -d` then publishes each service on a free port chosen by Docker. `scripts/dev-info.sh` prints:
- the project and mode;
- the frontend, backend and API-docs URLs;
- the PostgreSQL `localhost:<port>`, user and database (never the password);
- the data directory.

It exits non-zero when the stack is not running.

- **Fixed ports:** `FRONTEND_PORT`, `BACKEND_PORT` and `DB_PORT` set one service's host port in either mode. Unset ports stay at 5173/8000/5432 in default mode, or are chosen by Docker in worktree mode.
- **Changing ports:** Docker-chosen ports change when the containers are recreated. Re-run `scripts/dev-info.sh`, or set the port variables.
- **Native tools:** use the database port printed by `scripts/dev-info.sh`, e.g. `DATABASE_URL=postgresql+psycopg://viptop:viptop@localhost:<port>/viptop`.
- **Shared exports:** point every worktree's `VIPTOP_DATA_DIR` at one folder, e.g. `../data`.
- **Windows:** `COMPOSE_FILE` uses `;` as its separator. Alternatively, set `COMPOSE_PATH_SEPARATOR=:`.
- **Agents:** the `worktree-create` and `worktree-setup` skills (`.ai/skills/`) do these steps.

## Route planning

Supply the trusted inference product and input CSVs using the
[fill prediction runtime configuration](data/fill-prediction.md#application-demo-runtime).
Rebuild the backend after dependency changes and start the stack. Open
<http://localhost:5173/admin/routes> (use the assigned frontend port in worktree mode).
Route planning needs available stored trucks with matching waste carriers,
positive capacities and landfills with valid coordinates; add them through the
fleet screen. The explicit command below enables stored `Demo 1`–`Demo 150`
records using the carrier, capacity and landfill configured on `Demo 1`, adding
missing names and leaving unrelated trucks untouched:

```bash
docker compose exec backend uv run python -m app.interfaces.demo.fleet
```

Road geometry uses [OSRM's route API](https://project-osrm.org/docs/v5.24.0/api/#route-service)
with the visit order produced by the shared PyVRP route optimizer. `DEMO_OSRM_URL` defaults to
`https://router.project-osrm.org`; set it to a dedicated OSRM server for repeated
large runs. `DEMO_OSRM_REQUEST_INTERVAL_SECONDS` defaults to 1.1 (minimum 1) to
respect the public service's request rate. Requests send the selected stop
coordinates to that server. Road generation for 150 trucks can take several
minutes. The demo solves each carrier independently with capacity limits and
landfill reloads. Stop loads cover the selected due bins only, using the shared
fill-level volume assumptions from the collection planner. Optimizer distances
remain estimates from straight-line distances and a detour factor; displayed
paths use OSRM roads. Missing carrier fleets, missing bin capacities and stops
above every eligible truck capacity are reported as unserved.

The solver uses seed 0 and 1,000 iterations, with a 180-second safety limit per
carrier inside the fourteen-minute navigation deadline. It reads current bin
capacities and the first 150 eligible trucks selected in carrier round-robin
order, without saving plans. Rebuild the backend image to install the incoming
locked PyVRP dependency before running this flow. Solver imports occur only
when optimization runs, so a missing solver does not block API startup or
prediction.

Both Vite development and preview proxies and the prediction client allow a
15-minute prediction or navigation request. Configure any additional reverse proxy with an equally long
deadline. Each prediction scans its CSV without a result cache. Leaving the page
aborts the client request, but the backend scan can continue and reject another
prediction as busy until it finishes. Backend code reloads interrupt active
requests; finish editing before filming a run. Use one backend worker so the
in-process inference guard covers the demo server.

The repeatable command can also calculate road paths and report
truck/stop/bin counts and exact assigned-or-unserved coverage:

```bash
docker compose exec backend uv run python -m app.interfaces.demo --date 2026-09-14 --navigation
```

It reads the current fleet and data without saving routes or rebuilding plans.
Calculated road paths and per-stop legs are held in server memory for tracking,
with a one-hour lifetime and a maximum of three runs. Use one backend worker;
restarting the backend or evicting a run requires calculating a new plan.
`GET /demo/driving-route` reads one truck's calculated route using its `run_id`
and `truck_id`, without recalculation or database writes. The [Driver](driver.md) reads the
newest run of its forecast day from the same memory. Animation timing is
configured in `frontend/src/pages/demo/truck-demo-page.tsx`. Behavior specs:
[project date](../openspec/specs/project-date/spec.md),
[planning](../openspec/specs/demo-planning/spec.md),
[driving](../openspec/specs/truck-driving-demo/spec.md).

## Area analyst configuration and diagnostics

Set `OPENAI_API_KEY` and `OPENAI_MODEL` in the repository-root `.env` for the
backend. Choose a model that supports Responses function calling. Keep the key
out of `VITE_` variables, source files and logs. Empty values leave ordinary map
reads available. Recreate the backend after configuration changes:

```bash
docker compose up -d --force-recreate backend
```

The image packages `docs/agent-skills.md`, `docs/data-model.md` and
`docs/data/bin-days-columns.md`. Development mounts these files read-only at
`/app/agent-domain`; edit their canonical sources without rebuilding. Native
runs resolve the same sources from the repository root. Runtime dictionaries
include only sections delimited by `agent-runtime` comments; example export
statistics and rows are excluded. Tool documentation comes from the registry.

Run local diagnostics without an OpenAI key:

```bash
docker compose exec backend uv run python -m app.interfaces.analytics_agent.check --catalogue
docker compose exec backend uv run python -m app.interfaces.analytics_agent.check --guide
docker compose exec backend uv run python -m app.interfaces.analytics_agent.check --bbox 54.68 25.27 54.70 25.30 --project-date 2026-09-14
docker compose exec backend uv run python -m app.interfaces.analytics_agent.check --bbox 54.68 25.27 54.70 25.30 --project-date 2026-09-14 --tool get_service_summary --arguments '{"scope":"area","grouping":"waste_carrier","period":null}'
```

Local mode uses short rollback-only database snapshots and never calls a
provider. `--full` prints bounded JSON evidence. Native execution uses the
[backend setup](#native-backend) and `uv run python -m` with the same module.

Live execution is explicit:

```bash
docker compose exec backend uv run python -m app.interfaces.analytics_agent.check --bbox 54.68 25.27 54.70 25.30 --project-date 2026-09-14 --live
```

A live run has ceilings of 60 seconds, five model requests, twelve executed
tools, four tools per response, 16 KiB per tool result and 64 KiB of results per
run. Investigation ends by 45 seconds, reserving 15 seconds for synthesis.
The diagnostic reports request counts, durations, tool names and result bytes
without keys or raw provider exceptions. Exit codes are 0 for successful local
reads/complete live analysis, 1 for failed diagnostics, 2 for missing live
configuration and 3 for incomplete live analysis.

Behaviour and contracts: [area analyst](../openspec/specs/area-analytics-agent/spec.md),
[analytics tools](../openspec/specs/analytics-tools/spec.md).
