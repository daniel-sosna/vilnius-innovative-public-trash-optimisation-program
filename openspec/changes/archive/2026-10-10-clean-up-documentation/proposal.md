# Proposal

## Why

`README.md` has grown to about 940 lines. Every change added or extended its own section, so it now mixes setup, migration history, UI walkthroughs, API contracts already in the specs, and data-model details, with the same facts repeated in several places. Nobody reads it in practice. `docs/` has the same problem: 12 verification files (about 5,000 lines) are acceptance logs of finished changes, full of dates, machine paths and "historical" notes. Nothing in the project's governance says where documentation belongs, so the next change will add to the README again.

## What Changes

- Rewrite `README.md` as a short entry point with a line budget: what the project is, a **Quick Start**, the data pipeline as a table of commands, the current project structure and an index of `docs/`.
- Move operational detail into topic files under `docs/`: development setup (native backend/frontend, configuration, migrations, worktrees), the data model, and one file per data command (CSV import, bin population, bin-day calendar, collection plan, schedule sync, bin sync) with its options and modelling assumptions.
- Drop text that restates specs (UI walkthroughs, API validation rules, pixel-level map behaviour) and link the relevant `openspec/specs/<capability>/` instead.
- Remove all change history from the documentation: migration-revision narratives, branch-switching notes, "earlier", "now", "historical" wording and dates. The documentation describes the system as it is.
- Remove duplicated facts (native frontend commands, refill order of derived tables, the agent data check that `AGENTS.md` already holds).
- Move the 12 `docs/*-verification*.md` files into the archived change folders that created them. They are acceptance evidence for those changes, not reference documentation.
- Keep `docs/bin-days-columns.md` as a reference, moved next to the bin-day calendar doc and stripped of history.
- Add a documentation policy to `openspec/config.yaml`, so that proposals, tasks and apply runs keep the README short. It sets the README's scope and budget, says where detail goes, forbids history and restating specs, keeps verification evidence in change folders, and requires documentation tasks to name their target `docs/` file.
- Update pointers to the old README sections in `AGENTS.md`, `.env.example` and `.ai/skills/worktree-setup/SKILL.md`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `local-dev-environment`: the "Documented setup" requirement moves the worktree and port documentation from the README to the development guide, and requires a Quick Start in the README.

## Impact

- Documentation only: `README.md`, new and moved files under `docs/`, `AGENTS.md`, `.env.example`, `.ai/skills/worktree-setup/SKILL.md` and `openspec/config.yaml`.
- `openspec/changes/archive/<change>/` folders receive the verification files. Their contents are not edited, so relative links inside them may stop resolving. That is acceptable for archived evidence.
- No code, API, schema, Compose or runtime behaviour changes.
