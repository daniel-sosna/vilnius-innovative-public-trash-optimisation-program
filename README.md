# VipTop Waste Collection Optimisation

VipTop is a hackathon MVP for more efficient public waste-container collection in Vilnius. It stores the city's collection sites, bins and service history; builds resident estimates, a simulated bin-day calendar and a daily collection plan; and has a Lithuanian admin UI for trucks, sites and map analytics, plus a public resident request page. Fill prediction is a mock, and route optimisation does not exist yet.

React, TypeScript, Vite, Tailwind CSS and shadcn/ui · Python 3.12, FastAPI, SQLAlchemy and Alembic · PostgreSQL · Docker Compose

## Quick Start

You need Docker with Docker Compose and the CSV exports from a teammate.

1. Create `.env` and start the stack. Migrations run automatically.

   ```bash
   test -f .env || cp .env.example .env
   docker compose up --build -d
   ```

2. Put the exports in `backend/data/`: `sites_<digits>.csv`, `bins_<digits>.csv` and `bin_hist_<digits>.csv` are required. `bin_schedule_<digits>.csv` and `population_density_1ha.geojson` are needed for the [data pipeline](#data-pipeline).
3. Import them:

   ```bash
   docker compose exec backend uv run python -m app.interfaces.table_import
   ```

4. Open the frontend at <http://localhost:5173>. The backend is at <http://localhost:8000>, with its API reference at <http://localhost:8000/docs>.

Do not use `bin_sync` to get development data: it takes hours. To run several checkouts side by side or to run without Docker, see [Development](docs/development.md).

## Data pipeline

Run these in order after an import. Importing `bins` empties every derived table ([details](docs/data/import.md#what-an-import-replaces)). Each command runs as `docker compose exec backend uv run python -m app.interfaces.<module>`.

| Step | Module | Builds | Docs |
|---|---|---|---|
| 1 | `table_import` | `sites`, `bins`, `bin_hist` (optionally `bin_schedule`, `resident_requests`) from CSV | [import](docs/data/import.md) |
| 2 | `bin_population` | Estimated residents per bin | [bin population](docs/data/bin-population.md) |
| 3 | `bin_days --start ... --end ...` | Bin-day calendar with simulated collections | [bin days](docs/data/bin-days.md) |
| 4 | `collection_plan` | Sites to serve per carrier for a date (mock prediction) | [collection plan](docs/data/collection-plan.md) |

Source refreshes (the slow ones, used to update the shared exports):

| Module | Refreshes | Docs |
|---|---|---|
| `bin_schedule_sync` | VASA planned dates, current month (about 13 min) | [schedule sync](docs/data/bin-schedule-sync.md) |
| `bin_sync` | Sites, bins and history from VASA (hours) | [bin sync](docs/data/bin-sync.md) |

## Features

| Screen | URL | Spec |
|---|---|---|
| Role selection | `/` | – |
| Truck management | `/admin/trucks` | [truck-management](openspec/specs/truck-management/spec.md) |
| Collection sites, details, adding and deleting sites and bins | `/admin/sites`, `/admin/sites/{id}` | [collection-site-browsing](openspec/specs/collection-site-browsing/spec.md), [collection-site-management](openspec/specs/collection-site-management/spec.md) |
| Map analytics (landfills, bins, population density) | `/admin/map-analytics` | [map-analytics](openspec/specs/map-analytics/spec.md), [map-layers](openspec/specs/map-layers/spec.md) |
| Public resident emptying request | `/resident-request/{bin_id}` | [resident-requests](openspec/specs/resident-requests/spec.md) |

The admin screens have no authentication.

## Project structure

```text
.
├── frontend/src/
│   ├── pages/              # One folder per screen
│   └── components/         # Layout, maps, shared UI (shadcn/ui)
├── backend/
│   ├── alembic/            # Migrations (applied on startup)
│   └── app/
│       ├── core/           # Settings
│       ├── interfaces/     # HTTP routers and data CLIs (one package each)
│       ├── services/       # Application logic
│       ├── infrastructure/ # Database engine and ORM models
│       ├── integrations/   # VASA client
│       ├── ml/             # Fill prediction (mock)
│       └── optimization/   # Route optimisation (empty)
├── scripts/dev-info.sh     # URLs and data folder of the running stack
├── docs/                   # Reference documentation
└── openspec/               # Specs and changes (see AGENTS.md)
```

## Documentation

- [Development](docs/development.md): configuration, running without Docker, migrations, several worktrees at once
- [Data model](docs/data-model.md): tables and what their data means
- Data commands: [import](docs/data/import.md), [bin population](docs/data/bin-population.md), [bin days](docs/data/bin-days.md) ([columns](docs/data/bin-days-columns.md)), [collection plan](docs/data/collection-plan.md), [schedule sync](docs/data/bin-schedule-sync.md), [bin sync](docs/data/bin-sync.md)
- Behaviour: [`openspec/specs/`](openspec/specs/)
- HTTP API: `/docs` on the running backend
- Contributing with AI agents: [AGENTS.md](AGENTS.md)
