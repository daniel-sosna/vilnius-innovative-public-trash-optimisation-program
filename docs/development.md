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
