# Agent instructions

These instructions apply to every AI coding agent working in this repository (Claude Code, Codex and others).

## Project conventions

`openspec/config.yaml` is the single source of truth for project context, decision priorities and engineering principles. Read it before planning or changing anything, and follow it for all work, including work done outside the OpenSpec workflow:

- `context`: applies to all work.
- `rules`: apply when writing the matching proposal, spec, design or tasks artifacts.
- `operations.apply.guidance`: applies whenever you implement changes.

Do not copy these conventions into other files; update `openspec/config.yaml` instead.

## Workflow

Feature work goes through OpenSpec: propose → apply → archive.

| Step    | Claude Code               | Codex                      |
| ------- | ------------------------- | -------------------------- |
| Explore | `/openspec-explore`       | `$openspec-explore`        |
| Propose | `/openspec-propose`       | `$openspec-propose`        |
| Apply   | `/openspec-apply-change`  | `$openspec-apply-change`   |
| Archive | `/openspec-archive-change`| `$openspec-archive-change` |

The workflow skills call the `openspec` CLI (`npm install -g @fission-ai/openspec`).

### Shared skills

The OpenSpec skills exist once, in `.agents/skills/` (read by Codex). `.claude/skills` is a symlink to it, so Claude Code uses the same files. Never edit the skills by hand.

- Refresh after upgrading OpenSpec with `openspec update --force`. Without `--force`, OpenSpec may rewrite the shared files using only the Claude-specific wording.
- `.claude/commands/opsx/` is git-ignored: it would only duplicate the skills. To stop it being generated locally, run `openspec config set delivery skills` once (global setting).
- On Windows, enable symlinks before cloning (Developer Mode plus `git config --global core.symlinks true`).
