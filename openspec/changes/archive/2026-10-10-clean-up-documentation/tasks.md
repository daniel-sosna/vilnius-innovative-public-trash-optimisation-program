# Tasks

## 1. Documentation policy

- [x] 1.1 Add the documentation paragraph to `context` and the documentation entry to `rules.tasks` in `openspec/config.yaml` (design Decision 4). Verify that the file still parses (`openspec context --json` succeeds) and that `openspec instructions tasks --change clean-up-documentation --json` shows the new rule.

## 2. Move verification evidence

- [x] 2.1 `git mv` the 12 `docs/*-verification*.md` files into their archived change folders, following the table in design Decision 5. Verify that `ls docs/*verification*` finds nothing and each file exists at its new path.

## 3. Topic docs

- [x] 3.1 Write `docs/development.md` from the README's native backend/frontend, configuration, map style, API proxy/build, migration and worktree content, with no history and one copy of each command. Verify that the native backend and frontend commands match `backend/pyproject.toml`, `frontend/package.json` and `.env.example`, and that the worktree content covers worktree mode, the port variables, `VIPTOP_DATA_DIR` and `scripts/dev-info.sh` (`local-dev-environment` spec).
- [x] 3.2 Write `docs/data-model.md` with the tables and the meaning of their data (site grouping and averaged coordinates, nullable attributes, unverified capacity unit, history semantics, cascades, landfill catalog), with no migration narratives or inspection SQL. Verify the table and column names against `backend/app/infrastructure/models.py`.
- [x] 3.3 Write `docs/data/import.md`, `bin-population.md`, `bin-days.md`, `collection-plan.md`, `bin-schedule-sync.md` and `bin-sync.md` from the matching README sections. Keep commands, options, exit codes, durations, side effects and assumptions. Each side effect lives once, in `import.md`, and the other files link to it. Verify each documented command's options against its `--help` output (`docker compose exec backend uv run python -m app.interfaces.<module> --help`).
- [x] 3.4 `git mv docs/bin-days-columns.md docs/data/bin-days-columns.md`, remove its history wording, and repoint its README links to `bin-days.md` and `bin-population.md`. Verify that its links resolve.

## 4. README

- [x] 4.1 Rewrite `README.md` to the outline in design Decision 2 (description, Quick Start, data pipeline table, features table with spec links, current project structure, documentation index). Verify that it has at most 150 lines (`wc -l README.md`), that it contains no "revision", "earlier", "now", "historical" or "no longer" wording (`grep -inE`), and that the Quick Start runs as written on a fresh `docker compose down --volumes` stack with the CSV exports present (`local-dev-environment` spec, "Following the Quick Start").
- [x] 4.2 Check that nothing useful was lost, using the safety rule in design Decision 3. Extract the env var names, CLI flags and table names from `git show HEAD:README.md`, and confirm that each appears in the README, in `docs/` or in a spec. Restore any missing fact to the right `docs/` file.

## 5. Pointers and integration

- [x] 5.1 Update the references to old README sections in `AGENTS.md` (the import section and the worktree section), `.env.example` (the worktree comment) and `.ai/skills/worktree-setup/SKILL.md` (worktree background and "README order" of derived tables) so they point to the new files. Verify with `grep -rn "README" AGENTS.md .env.example .ai/` that each remaining reference resolves to an existing section.
- [x] 5.2 Check links across the repository. For every `.md` outside `openspec/changes/archive/` and `node_modules`, verify that each relative link and `#anchor` into `README.md` or `docs/` resolves, and that every `docs/` file is linked from the README index.
- [x] 5.3 Run `openspec validate clean-up-documentation` and verify that it passes.

## Workflow follow-up

- Archive the change after review. Archiving syncs the `local-dev-environment` delta into the main spec.
