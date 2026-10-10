## MODIFIED Requirements

### Requirement: Documented setup
The README SHALL contain a Quick Start section that takes a developer from a fresh clone to a running stack with imported collection data, using only Docker Compose commands, and SHALL say where to find the running services. The development guide in `docs/` SHALL explain worktree mode, the port variables, `VIPTOP_DATA_DIR` and how to find a stack's URLs with `scripts/dev-info.sh`, and the README SHALL link to it. `.env.example` SHALL list the worktree and port variables only as commented-out lines.

#### Scenario: Copying the example file
- **WHEN** a developer copies `.env.example` to `.env` without editing it
- **THEN** the stack runs in default mode on the default ports with `backend/data/` as its data directory

#### Scenario: Following the Quick Start
- **WHEN** a developer with Docker, a fresh clone and the CSV exports follows the README Quick Start step by step
- **THEN** the stack is running, the collection data is imported and the developer knows the frontend, backend and API-docs URLs

#### Scenario: Running several worktrees
- **WHEN** a developer wants to run a second checkout next to the first
- **THEN** the README links to the development guide, which explains worktree mode, the port variables, `VIPTOP_DATA_DIR` and `scripts/dev-info.sh`
