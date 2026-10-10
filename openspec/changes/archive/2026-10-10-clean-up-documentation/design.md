# Design

## Context

See proposal.md for the motivation. The facts that shape the approach:

- 20 archived changes each had a task like "add/update the README section ...". That task pattern caused the growth. `openspec/config.yaml` has no rule about documentation, and its `context` and `rules` are fed to every propose and apply run.
- 15 specs (about 240 requirements) already define UI behaviour, API contracts and validation. Most of the README's feature sections restate them.
- FastAPI serves an up-to-date API reference at `/docs`.
- Archived change folders already hold extra files (`runtime-setup.md`, `isolation-preflight.md`, `configuration-evidence.json`), so placing verification evidence there follows existing practice.
- Pointers to README sections exist in `AGENTS.md`, `.env.example`, `.ai/skills/worktree-setup/SKILL.md` and `docs/bin-days-columns.md`.

## Goals / Non-Goals

**Goals:**
- A README that can be read in a few minutes and gets a developer running.
- Each fact stated once, in a predictable place.
- A rule that future agents apply automatically, through `config.yaml`.

**Non-Goals:**
- Rewriting specs. They may contain "as before this change"-style wording, and that is left alone.
- Editing the contents of the moved verification files or other archived artifacts.
- Turning manual verification procedures into scripts.
- Changing `.claude/`, `.agents/` or `.github/` skill files, which are generated.

## Decisions

### 1. Target layout

```
README.md                    entry point, <= 150 lines
docs/
  development.md             native backend/frontend, configuration (env vars),
                             map style, API proxy and builds, migrations,
                             worktrees and ports, data directory
  data-model.md              tables and what their data means
  data/
    import.md                table_import: files, data dir, side effects, exit codes
    bin-population.md        command, options, assumptions
    bin-days.md              command, options, eligibility, assumptions
    bin-days-columns.md      moved from docs/, history and README links removed
    collection-plan.md       command, options, mock-prediction assumption, get_plan contract
    bin-schedule-sync.md     command, options, snapshot behaviour, duration
    bin-sync.md              VASA sync: scope, options, cleanup, settings
```

A `data/` subfolder groups the pipeline commands, which are the most frequently extended topic. A single `data-pipeline.md` was rejected: it would be about 300 lines and would become the next README. One file per README section was also rejected: UI sections have nothing left to say once spec restatements are dropped.

### 2. README outline

1. Title and a two-to-three-sentence description of what exists today.
2. **Quick Start**: copy `.env`, `docker compose up --build -d`, put the CSV exports (and the density GeoJSON) in the data directory, run `table_import`, open the URLs. It also points to `scripts/dev-info.sh` for worktree mode and warns in one line not to use `bin_sync` for development data.
3. **Data pipeline**: a table in run order with the columns command | builds | doc link. The rows are: import, then bin population, then bin days, then collection plan, plus schedule sync and bin sync as source refreshes. The refill order is stated here once.
4. **Features**: a table with the columns screen | URL | spec link. The screens are trucks, sites and site management, map analytics and the resident request page.
5. **Project structure**: the current tree, including the `bin_population`, `bin_days` and `collection_plan` interfaces.
6. **Documentation**: an index of `docs/`, a link to `openspec/specs/`, and `/docs` for the API.

### 3. Content triage

Each paragraph of the current README and `bin-days-columns.md` goes to exactly one bucket:

| Bucket | Content | Destination |
|---|---|---|
| Keep | Setup steps, commands, options, exit codes, durations, side effects, env vars, modelling and data assumptions, meaning of stored data (unverified capacity unit, averaged site coordinates, history uniqueness, cascades), code contracts used by other components (`get_plan`) | README (Quick Start/pipeline) or the matching `docs/` file |
| Drop: spec restated | UI walkthroughs, labels, toasts, layout, map clustering pixels, API field lists, validation rules, status codes | Link to the spec |
| Drop: history | Migration revision narratives, branch-switching instructions, "replace old setting", "now runs from main", "historical evidence", dates | Deleted |
| Drop: duplicate | Repeated native frontend commands, repeated refill order, the AI-agent data check (kept in `AGENTS.md`) | Single remaining copy |
| Drop: noise | Inspection SQL snippets, "outside this feature" lists | Deleted |

Safety rule: before dropping a sentence as "spec restated", check that a spec covers it. If no spec does and it is still true and useful, keep it in the nearest `docs/` file. The assumptions sections are always kept, because the project requires explicit assumptions.

### 4. Documentation policy in `openspec/config.yaml`

The policy goes in the `context` field rather than in `AGENTS.md`, because `AGENTS.md` defers to `config.yaml` as the single source of truth, and `context` reaches every artifact and the apply phase. A short `tasks` rule targets the specific mechanism that caused the growth. Draft text:

`context`, a new paragraph after the engineering principles:

```
Documentation (applies to all work, inside or outside OpenSpec):
- README.md is only the entry point: short description, Quick Start, data
  pipeline table, features table, project structure and an index of docs/.
  Keep it under 150 lines. Add a row or link there, never a feature section.
- Put detail in the topic file under docs/ (development.md, data-model.md,
  data/<command>.md). Extend the existing file for a topic before creating a
  new one; list every new file in the README index.
- Behaviour is specified in openspec/specs/. Do not restate UI behaviour, API
  contracts or validation rules in docs; link the spec. Document only what
  the specs and code do not tell a reader: how to run things, configuration,
  options, side effects, durations and assumptions.
- Describe the current state only: no change history, migration narratives,
  dates, "now", "previously", "no longer" or "historical". Replace outdated
  text instead of appending to it.
- State each fact once and link to it elsewhere. Be concise: short
  sentences, bullets and tables; no overexplaining.
- Manual verification steps and evidence belong to the change
  (openspec/changes/<name>/), never to docs/.
```

`rules.tasks`, a new entry:

```
- A documentation task names the docs/ file it updates and what it adds or
  replaces; never "add a README section". Touch README only when the Quick
  Start, pipeline table, features table, structure or docs index changes.
```

A separate `docs/CONTRIBUTING`-style file was considered. It was rejected because agents only reliably see what `config.yaml` injects and what `AGENTS.md` points to.

### 5. Moving the verification files

Each file is moved with `git mv`, keeping its name, into the archived change whose commit created it:

| File | Archived change |
|---|---|
| `data-foundation-verification.md` | `2026-10-07-establish-data-foundation` |
| `table-import-verification.md` | `2026-10-09-add-table-csv-import` |
| `collection-site-browsing-verification.md` | `2026-10-09-bins-ui` |
| `collection-site-browsing-verification-history.md` | `2026-10-09-bins-ui` |
| `truck-management-verification.md` | `2026-10-09-truck-ui` |
| `bin-population-verification.md` | `2026-10-10-add-bin-resident-factor` |
| `collection-plan-verification.md` | `2026-10-10-add-collection-plan` |
| `bin-day-calendar-verification.md` | `2026-10-10-bin-day-calendar` |
| `collection-site-management-verification.md` | `2026-10-10-bins-ui-update` |
| `map-analytics-verification.md` | `2026-10-10-layer-map` |
| `population-map-verification.md` | `2026-10-10-layer-map-pop` |
| `resident-request-verification.md` | `2026-10-10-resident-reqs` |

Several later changes also edited some of these files. Assigning each file to the change that created it is simple and deterministic, and git history keeps the rest. The file contents are not edited, so their links to `../README.md` may no longer resolve. That is acceptable for archived evidence.

## Risks / Trade-offs

- [A useful fact is dropped because it was assumed to be in a spec] → Apply the safety rule in Decision 3. Afterwards, grep the old README (from git) for env var names, command flags and table names, and confirm that each still appears in the new docs.
- [The 150-line budget pushes Quick Start detail out] → Quick Start has priority. Features and structure can be trimmed first.
- [Agents ignore the policy] → It sits in `context`, which every OpenSpec instruction includes, and `AGENTS.md` already tells agents to read `config.yaml` before any task.
- [Broken links after the moves] → A final check greps every `.md` outside the archive for links into `docs/` and `README.md#...` anchors and verifies that they resolve.

## Migration Plan

This is a single documentation commit with nothing to deploy. Rollback is `git revert`.
