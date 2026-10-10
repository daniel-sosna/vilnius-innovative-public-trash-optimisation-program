# Proposal

## Why

Some developers work on several branches at once through git worktrees. Every checkout's Docker Compose stack asks for the same host ports (5173, 8000, 5432), so only one stack can run at a time. Each new worktree also starts without `.env` and without the CSV exports, so getting it running takes several manual steps. Developers who work in a single checkout must see no change.

## What Changes

- Compose host ports become configurable through `FRONTEND_PORT`, `BACKEND_PORT` and `DB_PORT`. When they are unset, the ports stay 5173, 8000 and 5432.
- A new opt-in Compose override file publishes each service on a free port chosen by Docker, unless that service's port variable is set. A checkout turns it on with one `COMPOSE_FILE` line in its `.env`.
- A new host script, `scripts/dev-info.sh`, prints the running stack's URLs: frontend, backend, API docs, database and the data directory in use. The README explains how to find a stack's URLs.
- A new `VIPTOP_DATA_DIR` variable points the backend container's data directory at a host folder, so worktrees can share one set of exports. `table_import` and `bin_population` also read it when run natively. An explicit `--dir` or `--file` still wins.
- `AGENTS.md` and the README's data rules point to the configured data directory instead of only `backend/data/`.
- Two new AI agent skills, available to Claude Code, Codex and GitHub Copilot:
  - `worktree-setup` prepares an existing checkout to run alongside others.
  - `worktree-create` creates a git worktree, then runs `worktree-setup`.

  Both stop and ask the developer when something is unusual. Each skill has one full copy; each agent's folder holds a small pointer file.
- `.env.example` documents the new variables as commented-out lines, so copying it changes nothing.

## Capabilities

### New Capabilities

- `local-dev-environment`: how the local Compose stack publishes ports, runs next to other checkouts' stacks, reports its URLs and finds its data directory.
- `worktree-agent-skills`: the AI agent skills that create and set up a worktree, and when they must ask the developer.

### Modified Capabilities

- `table-csv-import`: the default export directory follows `VIPTOP_DATA_DIR` when set; `--dir` still overrides it.
- `bin-resident-allocation`: the default density file is looked up in the configured data directory; `--file` still overrides it.

## Impact

- **Infrastructure:**
  - `docker-compose.yml`: port mappings, plus a data-directory bind mount for the backend.
  - New `docker-compose.worktree.yml`.
  - `.env.example`.
- **Backend:** default path resolution in `app/interfaces/table_import/cli.py` and `app/interfaces/bin_population/cli.py`, and possibly a settings field in `app/core/config.py`. Container paths, the API and the database are unchanged.
- **Tooling and docs:**
  - New `scripts/dev-info.sh`.
  - New skills in `.ai/skills/`, with pointer files in `.claude/skills/`, `.agents/skills/` and `.github/skills/`.
  - Edits to `README.md` and `AGENTS.md`.
- **Single-branch developers:** no change in behaviour, ports or commands.

**Assumptions and uncertainties:**
- Developers run Linux or macOS. `COMPOSE_FILE` uses `:` as the separator; Windows uses `;`.
- `openspec update` keeps skill folders it did not generate. This was checked with OpenSpec 1.14.1 in a scratch copy.
- Vite live reload still has to be confirmed when the host port differs from 5173.
- Claude Code, Codex and Copilot all follow the pointer files. This has to be confirmed for each agent.
