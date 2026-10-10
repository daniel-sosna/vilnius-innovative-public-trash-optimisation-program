# local-dev-environment Specification

## Purpose

Lets developers run the local Docker Compose stack, either one checkout at a time on the usual ports or several git worktrees side by side without port conflicts, and find each stack's URLs and data directory.

## Requirements

### Requirement: Unchanged default ports
When no port variable is set and the worktree mode is off, the stack SHALL publish the frontend on host port 5173, the backend on 8000 and PostgreSQL on 5432, as before this change. `docker compose up` SHALL need no new variables, files or commands.

#### Scenario: Single-branch developer
- **WHEN** a developer copies `.env.example` to `.env` and runs `docker compose up --build -d`
- **THEN** the frontend is at `http://localhost:5173`, the backend at `http://localhost:8000` and PostgreSQL at `localhost:5432`

### Requirement: Explicit host ports
`FRONTEND_PORT`, `BACKEND_PORT` and `DB_PORT` SHALL set the host port of the frontend, backend and PostgreSQL, in both default and worktree mode. Ports inside the stack SHALL stay the same, so services keep reaching each other as before.

#### Scenario: Override one port
- **WHEN** `.env` sets `FRONTEND_PORT=5180` and nothing else about ports
- **THEN** the frontend is published on 5180, the backend on 8000 and PostgreSQL on 5432, and the frontend's API calls still reach the backend

#### Scenario: Explicit port in worktree mode
- **WHEN** worktree mode is on and `BACKEND_PORT=8010` is set
- **THEN** the backend is published on 8010 and the other services on Docker-chosen ports

### Requirement: Opt-in worktree mode with free ports
A checkout SHALL turn on worktree mode by adding one documented `COMPOSE_FILE` line to its `.env`. In worktree mode, every service without an explicit port variable SHALL be published on a free host port chosen by Docker. No default port SHALL also be published.

#### Scenario: Two worktrees at once
- **WHEN** two checkouts both have worktree mode on and no port variables, and both run `docker compose up -d`
- **THEN** both stacks start, and none of their services uses 5173, 8000 or 5432 or the same host port as the other

#### Scenario: Worktree next to a single-branch stack
- **WHEN** one checkout runs in default mode and another in worktree mode
- **THEN** both stacks start, and the default-mode stack keeps 5173, 8000 and 5432

### Requirement: Separate state per checkout
Stacks of different checkouts SHALL use separate containers, networks, databases and dependency volumes, so starting, stopping or resetting one stack does not affect another.

#### Scenario: Reset one worktree
- **WHEN** a developer runs `docker compose down --volumes` in one worktree while another worktree's stack is running
- **THEN** only the first worktree's database and volumes are removed

### Requirement: Stack information command
`scripts/dev-info.sh`, run from a checkout on the host, SHALL print:
- the Compose project name and whether ports are fixed or Docker-chosen;
- the frontend, backend and API-docs URLs;
- the PostgreSQL host address and port;
- the host data directory mounted into the backend.

It SHALL never print the database password.

#### Scenario: Running worktree stack
- **WHEN** a worktree-mode stack is running and the developer runs `scripts/dev-info.sh`
- **THEN** it prints clickable `http://localhost:<port>` URLs for the frontend, backend and `/docs` that open the running services, and the PostgreSQL `localhost:<port>`

#### Scenario: Stack not running
- **WHEN** the checkout's stack is stopped
- **THEN** the script says that the stack is not running and exits with a non-zero code

#### Scenario: Default-mode stack
- **WHEN** a default-mode stack is running
- **THEN** the script prints ports 5173, 8000 and 5432

### Requirement: Configurable shared data directory
`VIPTOP_DATA_DIR` SHALL select the host folder mounted as the backend container's data directory. When it is unset, the data directory SHALL be `backend/data/` as before. A relative value SHALL be resolved from the repository root.

#### Scenario: Shared exports
- **WHEN** two worktrees set `VIPTOP_DATA_DIR` to the same folder containing the CSV exports
- **THEN** `table_import` run inside either backend container finds those exports without copying them into `backend/data/`

#### Scenario: Unset variable
- **WHEN** `VIPTOP_DATA_DIR` is not set
- **THEN** the backend container's data directory shows the contents of `backend/data/`

### Requirement: Documented setup
The README SHALL explain worktree mode, the port variables, `VIPTOP_DATA_DIR` and how to find a stack's URLs with `scripts/dev-info.sh`. `.env.example` SHALL list the new variables only as commented-out lines.

#### Scenario: Copying the example file
- **WHEN** a developer copies `.env.example` to `.env` without editing it
- **THEN** the stack runs in default mode on the default ports with `backend/data/` as its data directory
