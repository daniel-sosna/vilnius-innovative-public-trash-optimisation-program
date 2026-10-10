---
name: worktree-setup
description: Prepare an existing checkout (git worktree) to run its own Docker Compose stack next to other checkouts' stacks - creates .env in worktree mode, points it at the shared data folder, starts the stack, imports the CSV exports and prints the URLs. Use when the user wants to set up, start or get a worktree running, or says "worktree setup".
---

# worktree-setup

Prepare the current checkout to run in worktree mode (Docker-chosen host ports) and fill it with collection data. Run every command from the checkout's root. See `docs/development.md` ("Several worktrees at once") for background.

## Rules

- **Ask, don't decide.** In any situation marked **ASK** below, describe what you found, then wait for the developer's choice. Do not pick for them.
- Never run `bin_sync`; collection data comes only from CSV exports (`AGENTS.md`).
- Never change Docker settings or permissions, never remove volumes, and never edit an existing `.env` without the developer's explicit agreement.

## Steps

1. **Docker reachable?** Run `docker info`. If it fails: **ASK-STOP** - report the error and stop. Change nothing about Docker settings or permissions.

2. **`.env`.**
   - Missing: create it from `.env.example`, then append the lines from step 3.
   - Present: **ASK** - show the exact lines you would add or change (`COMPOSE_FILE`, `VIPTOP_DATA_DIR`) and edit nothing until the developer agrees.
   - Worktree mode line: `COMPOSE_FILE=docker-compose.yml:docker-compose.worktree.yml` (on Windows the separator is `;`, or set `COMPOSE_PATH_SEPARATOR`).

3. **Shared data folder** (`VIPTOP_DATA_DIR`).
   - If `../data/` (in the checkout's parent folder) holds `sites_<digits>.csv`, `bins_<digits>.csv` and `bin_hist_<digits>.csv`, use `VIPTOP_DATA_DIR=../data` without asking.
   - Otherwise **ASK** where the data folder is, and check the folder they name for the three exports. Write the path they give (relative paths are resolved from the repository root).
   - If the chosen folder lacks any of the three exports: **ASK-STOP** - stop before starting or importing and ask the developer to add the exports. Do not start a VASA synchronization.
   - Docker creates a missing bind-mount folder empty (often root-owned), so the folder must exist before `up`.

4. **Several exports for one table.** List the files in the data folder. If a table (`sites`, `bins`, `bin_hist`) has more than one `<table>_<digits>.csv`, **ASK** the developer to confirm the newest one (highest digits), which is the one the import uses.

5. **Leftover volumes.** Run `docker volume ls --filter label=com.docker.compose.project=$(basename "$PWD")` (the Compose project is the folder name, lowercased; `docker compose config --format json` shows `name`). If volumes exist, **ASK**: explain they may hold another branch's database, and ask whether to reuse them or remove them (`docker compose down --volumes`) before starting. Remove nothing without a yes.

6. **Explicit ports.** If `.env` sets `FRONTEND_PORT`, `BACKEND_PORT` or `DB_PORT`, check each is free (for example `ss -ltn "sport = :<port>"`). For a taken port, **ASK**: name the port and the variable and ask whether to change or remove it.

7. **Start.** `docker compose up --build -d`.

8. **Wait for the backend.** Startup runs migrations first. Get the backend URL from `scripts/dev-info.sh`, then poll `<backend>/docs` until it answers 200 (give up and report logs from `docker compose logs backend` after about two minutes).

9. **Import.** `docker compose exec -T backend uv run python -m app.interfaces.table_import`. It discards the current contents of the imported tables, which is expected for a fresh stack; with reused volumes the developer already agreed in step 5. Report the row counts.

10. **Derived tables.** The import reports tables it emptied (`bin_population`, `bin_days`, ...) with their refill commands. List them in the data-pipeline order from the README (bin population, then the bin-day calendar, then the collection plan) and **ASK** whether to run them. Bin population needs `population_density_1ha.geojson` in the data folder; if it is missing, say so and ask the developer to add it.

11. **Show the result.** Run `scripts/dev-info.sh` and show its output to the developer: project, mode, URLs, database port, data directory.

## Finish

Report what was changed (files edited, containers started, rows imported) and the URLs. Ports are Docker-chosen and change when containers are recreated; `scripts/dev-info.sh` prints them again.
