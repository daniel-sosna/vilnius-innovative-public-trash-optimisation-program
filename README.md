# VipTop Waste Collection Optimisation

VipTop MVP for exploring more efficient public waste-container collection in Vilnius. This repository currently contains only the technical foundation; product, prediction, and route-optimisation features will be added later.

## Technologies

- React, TypeScript, Vite, Tailwind CSS, and shadcn/ui
- Python 3.12, FastAPI, Uvicorn, SQLAlchemy, psycopg, and pydantic-settings
- PostgreSQL
- Docker Compose

## Project structure

```text
.
├── frontend/                # React web application
├── backend/
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
