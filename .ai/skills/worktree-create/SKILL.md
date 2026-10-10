---
name: worktree-create
description: Create a new git worktree for a branch and set it up to run its own Docker stack next to other checkouts. Use when the user wants a new worktree or a parallel checkout for a branch, or says "worktree create". Runs worktree-setup in the new folder.
---

# worktree-create

Create a git worktree for a branch the developer names, then prepare it with `worktree-setup` (`.ai/skills/worktree-setup/SKILL.md`).

## Rules

- **Ask, don't decide.** In any situation marked **ASK** below, describe what you found and wait for the developer's choice.
- Never run `bin_sync`. Never delete worktrees, branches or volumes unless the developer asks.

## Steps

1. **Branch name.** Use the branch the developer named; ask if none was given.

2. **Layout.** Run `git worktree list --porcelain`. Ignore bare entries. If every other worktree is a folder under one parent, the new worktree goes to `<parent>/<branch with "/" replaced by "-">`. Otherwise **ASK** where to put it.

3. **Existing folder or branch.** If the target folder already exists, or the requested new branch already exists locally: **ASK** whether to use the existing branch, pick another name, or stop.

4. **Remote-only branch.** Run `git fetch` and check `git branch -r`. If the branch exists on a remote but not locally: **ASK** whether to track the remote branch or create a new one.

5. **Create.**
   - New branch: `git worktree add -b <branch> <folder> <base>`. `<base>` is `main` (after the fetch, preferably `origin/main`) unless the developer names another base.
   - Existing local branch: `git worktree add <folder> <branch>`.
   - Tracking a remote branch: `git worktree add --track -b <branch> <folder> <remote>/<branch>`.

6. **Set up.** Change into the new folder and follow `worktree-setup` (`.ai/skills/worktree-setup/SKILL.md`) from step 1, including every **ASK** in it.

## Finish

Report the worktree path, branch, base, and the stack information printed by `scripts/dev-info.sh`.
