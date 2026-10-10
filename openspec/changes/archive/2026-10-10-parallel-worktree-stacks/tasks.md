# Tasks

## 1. Configurable and worktree-mode ports

- [x] 1.1 In `docker-compose.yml`, change the three port mappings to `${FRONTEND_PORT:-5173}:5173`, `${BACKEND_PORT:-8000}:8000` and `${DB_PORT:-5432}:5432`. Verify that `docker compose config` with no port variables shows published 5173/8000/5432, and that `FRONTEND_PORT=5180 docker compose config` shows 5180 for the frontend only.
- [x] 1.2 Add `docker-compose.worktree.yml`, which uses `ports: !override` with `"${X_PORT:+${X_PORT}:}<container port>"` for the frontend, backend and db. Verify with `COMPOSE_FILE=docker-compose.yml:docker-compose.worktree.yml docker compose config`:
  - no service has a published port when no variable is set;
  - `BACKEND_PORT=8010` publishes only the backend on 8010;
  - 5173, 8000 and 5432 never appear.
- [x] 1.3 Add commented-out `COMPOSE_FILE`, `FRONTEND_PORT`, `BACKEND_PORT` and `DB_PORT` lines with one-line explanations to `.env.example`. Verify that a `.env` copied unchanged from it still resolves to 5173/8000/5432.
- [x] 1.4 Runtime check: start this checkout in worktree mode while a default-mode stack runs from another checkout. Verify that:
  - both stacks start;
  - the worktree frontend loads at its Docker-chosen port;
  - `/api` calls reach its own backend;
  - editing a frontend file live-reloads the page.

  If live reload fails, fix it in the Vite config as design.md (Risks) describes and repeat the check.

## 2. Stack information script

- [x] 2.1 Add an executable `scripts/dev-info.sh` as described in design.md Decision 3. It prints the project, mode, frontend/backend/docs URLs, database `localhost:<port>` with user and database name (no password) and the mounted data directory, and exits non-zero when the stack is not running. Verify by running it against:
  - the worktree-mode stack from 1.4, where every printed URL opens the service;
  - a default-mode stack, which prints 5173/8000/5432;
  - a stopped stack, which gives a message and a non-zero exit code.
- [x] 2.2 Add a README section on running several worktrees at once. It covers worktree mode, the port variables, finding URLs with `scripts/dev-info.sh`, ports changing when containers are recreated, the database port for native tools and the Windows `COMPOSE_PATH_SEPARATOR` note. Point "The services are available at" to the script for worktree mode. Verify that following the section in a fresh worktree gives a running stack and its URLs.

## 3. Shared data directory

- [x] 3.1 Add the backend volume `${VIPTOP_DATA_DIR:-./backend/data}:/app/data` to `docker-compose.yml`, without adding the variable to `environment`. Verify that:
  - without the variable, `docker compose exec backend ls /app/data` shows the contents of `backend/data/`;
  - with `VIPTOP_DATA_DIR=../data`, it shows the shared exports;
  - `docker compose exec backend env` does not contain `VIPTOP_DATA_DIR`.
- [x] 3.2 Add the optional data-directory setting and a shared helper that resolves `VIPTOP_DATA_DIR` (relative values from the repository root, otherwise `backend/data/`). Use it as the default for `table_import --dir` and `bin_population --file` (`<dir>/population_density_1ha.geojson`), keeping explicit arguments first and existing error messages naming the resolved path. Verify natively from `backend/`:
  - with `VIPTOP_DATA_DIR=../../data` exported (or set in the root `.env`), `uv run python -m app.interfaces.table_import` reports files from that folder;
  - `--dir` overrides it;
  - a missing density file in that folder makes `bin_population` exit 1 naming the resolved path.
- [x] 3.3 Update the docs:
  - `.env.example`: add a commented-out `VIPTOP_DATA_DIR` line.
  - README: in "Import table CSV exports", "Bin population" and the "For AI agents" note, describe the configured data directory and precedence.
  - `AGENTS.md`: update the data rule to check the configured data directory.
  - `docs/table-import-verification.md`, `docs/bin-population-verification.md`, `docs/bin-day-calendar-verification.md`: update any `backend/data` instruction that now depends on the variable.

  Verify that every changed command in those docs runs as written.
- [x] 3.4 Runtime check: in a worktree-mode stack with `VIPTOP_DATA_DIR` set to the shared folder, run `docker compose exec backend uv run python -m app.interfaces.table_import`. Verify that it imports the shared exports and that `scripts/dev-info.sh` shows that folder as the data directory.

## 4. Agent skills

- [x] 4.1 Write `.ai/skills/worktree-setup/SKILL.md`, which follows design.md Decision 6 and every ask-first scenario in specs/worktree-agent-skills. Verify that each scenario in that spec maps to a step or stop condition in the skill.
- [x] 4.2 Write `.ai/skills/worktree-create/SKILL.md`, which creates the worktree as in design.md Decision 6 and then follows `worktree-setup`. Verify the same mapping against its scenarios.
- [x] 4.3 Add pointer `SKILL.md` files for both skills under `.claude/skills/`, `.agents/skills/` and `.github/skills/`, with the canonical `name`/`description` frontmatter and a body that defers to `.ai/skills/<name>/SKILL.md`. Mention the skills and the `.ai/skills/` location in `AGENTS.md`. Verify that `openspec update --force` leaves all six pointer files unchanged.
- [ ] 4.4 Check the agents: confirm that Claude Code, Codex and GitHub Copilot each list both skills and, when invoked, read the canonical file. If any agent does not, stop and switch to generated copies plus a CI check as design.md Decision 5 describes, after recording the deviation.
- [x] 4.5 End-to-end check: use `worktree-create` from an agent to create a throwaway branch worktree while another checkout's stack runs. Verify that:
  - the skill asks at the expected points, for example when volumes are left over from a removed worktree with the same name;
  - the skill uses the sibling `../data` without asking when it holds the exports, and asks for the folder when it doesn't;
  - it ends with a running stack, imported data and the `dev-info` output.

  Then remove the throwaway worktree, its branch and its volumes.

## Workflow follow-up

- Archive the change after the team has reviewed it.
