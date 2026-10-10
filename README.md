# VipTop Waste Collection Optimisation

VipTop is a hackathon MVP for more efficient public waste-container collection in Vilnius. It stores collection sites, bins and service history; builds resident estimates, a simulated bin-day calendar and a daily collection plan; and has a Lithuanian admin UI and public resident request page. Offline fill prediction provides a trained standalone package; the database collection plan uses a mock predictor. Route optimisation is not implemented.

React, TypeScript, Vite, Tailwind CSS and shadcn/ui · Python 3.12, FastAPI, SQLAlchemy and Alembic · PostgreSQL · Docker Compose

## Quick Start

You need Docker with Docker Compose and the CSV exports from a teammate.

1. Create `.env` and start the stack. Migrations run automatically.

   ```bash
   test -f .env || cp .env.example .env
   docker compose up --build -d
   ```

2. Put the exports in `backend/data/`: `sites_<digits>.csv`, `bins_<digits>.csv` and `bin_hist_<digits>.csv` are required. `bin_schedule_<digits>.csv` and `population_density_1ha.geojson` are needed for the [data pipeline](#data-pipeline). `vilnius_seniuniju_ribos.geojson` and `service_zones.geojson` feed the district and service-zone map layers.
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
| 1 | `table_import` | `sites`, `bins`, `bin_hist` (optionally `bin_schedule`, `resident_requests`) from CSV, plus district boundaries and service zones from GeoJSON | [import](docs/data/import.md) |
| 2 | `bin_population` | Estimated residents per bin | [bin population](docs/data/bin-population.md) |
| 3 | `bin_days --start ... --end ...` | Bin-day calendar with simulated collections | [bin days](docs/data/bin-days.md) |
| 4 | `collection_plan` | Sites to serve per carrier for a date (mock prediction) | [collection plan](docs/data/collection-plan.md) |

The offline CSV workflow uses separate optional dependencies and does not need a database:

| Stage | Command from repository root | Docs |
|---|---|---|
| Base exports and synthetic fill/QR labels | `python scripts/prepare_training_data.py`, then `python scripts/fill_qr.py` | [fill/QR generation](docs/data/fill-qr.md) |
| Train, compare and package fill prediction | From `backend/`: `python -m app.ml.run --config configs/ml.yaml` | [fill prediction](docs/data/fill-prediction.md) |

Other commands:

| Module | Does | Docs |
|---|---|---|
| `district_boundaries` | Loads only the district boundaries | [district boundaries](docs/data/district-boundaries.md) |
| `service_zones` | Loads only the service zones | [service zones](docs/data/service-zones.md) |
| `bin_schedule_sync` | Refreshes VASA planned dates for the current month (about 13 min) | [schedule sync](docs/data/bin-schedule-sync.md) |
| `bin_sync` | Refreshes sites, bins and history from VASA (takes hours) | [bin sync](docs/data/bin-sync.md) |

## Features

| Screen | URL | Spec |
|---|---|---|
| Role selection | `/` | – |
| Truck management | `/admin/trucks` | [truck-management](openspec/specs/truck-management/spec.md) |
| Collection sites, details, adding and deleting sites and bins | `/admin/sites`, `/admin/sites/{id}` | [collection-site-browsing](openspec/specs/collection-site-browsing/spec.md), [collection-site-management](openspec/specs/collection-site-management/spec.md) |
| Map analytics (landfills, bins, population density, districts, service zones) | `/admin/map-analytics` | [map-analytics](openspec/specs/map-analytics/spec.md), [map-layers](openspec/specs/map-layers/spec.md) |
| Public resident emptying request | `/resident-request/{bin_id}` | [resident-requests](openspec/specs/resident-requests/spec.md) |
| Standalone next-day fill prediction | Offline Python package | [daily-fill-prediction](openspec/specs/daily-fill-prediction/spec.md) |

The admin screens have no authentication.

## Project structure

```text
.
├── frontend/src/
│   ├── pages/              # One folder per screen
│   └── components/         # Layout, maps, shared UI (shadcn/ui)
├── backend/
│   ├── alembic/            # Migrations (applied on startup)
│   ├── configs/ml.yaml     # Offline ML paths, periods and resource limits
│   ├── requirements-ml.txt # Optional research dependencies
│   ├── viptop_fill/        # Portable feature construction and inference
│   ├── tests/ml/           # Focused ML checks
│   ├── data/               # Ignored exports, analysis and model delivery
│   └── app/
│       ├── core/           # Settings
│       ├── interfaces/     # HTTP routers and data CLIs (one package each)
│       ├── services/       # Application logic
│       ├── infrastructure/ # Database engine and ORM models
│       ├── integrations/   # VASA client
│       ├── ml/             # Offline ML stages and the collection-plan mock
│       └── optimization/   # Route optimisation (empty)
├── scripts/                # dev-info.sh and offline data utilities
├── docs/                   # Reference documentation
└── openspec/               # Specs and changes (see AGENTS.md)
```

## Documentation

- [Development](docs/development.md): configuration, running without Docker, migrations, several worktrees at once
- [Data model](docs/data-model.md): tables and what their data means
- Data commands: [import](docs/data/import.md), [bin population](docs/data/bin-population.md), [bin days](docs/data/bin-days.md) ([columns](docs/data/bin-days-columns.md)), [collection plan](docs/data/collection-plan.md), [district boundaries](docs/data/district-boundaries.md), [service zones](docs/data/service-zones.md), [schedule sync](docs/data/bin-schedule-sync.md), [bin sync](docs/data/bin-sync.md)
- Offline data/ML: [fill/QR generation](docs/data/fill-qr.md), [fill prediction](docs/data/fill-prediction.md)
- Behaviour: [`openspec/specs/`](openspec/specs/)
- HTTP API: `/docs` on the running backend
- Contributing with AI agents: [AGENTS.md](AGENTS.md)
