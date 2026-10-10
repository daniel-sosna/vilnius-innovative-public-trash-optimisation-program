# Spec Delta

## Purpose

Gives developers AI agent skills that create a git worktree and prepare it to run its own local stack next to other checkouts. The skills stop and ask the developer whenever the situation is not routine.

## ADDED Requirements

### Requirement: Skills available to every supported agent
The `worktree-setup` and `worktree-create` skills SHALL be discoverable and usable from Claude Code, Codex and GitHub Copilot. Each skill's instructions SHALL exist in one maintained copy, and every agent SHALL run the same steps.

#### Scenario: Agent lists the skills
- **WHEN** a developer opens the repository in Claude Code, Codex or GitHub Copilot
- **THEN** the agent offers both `worktree-setup` and `worktree-create`

#### Scenario: Instructions change
- **WHEN** a maintainer edits a skill's steps
- **THEN** only the one maintained copy changes, and all three agents follow the new steps

#### Scenario: OpenSpec regenerates its files
- **WHEN** `openspec update` regenerates the agent folders
- **THEN** both skills remain available

### Requirement: Set up an existing checkout
`worktree-setup` SHALL prepare a checkout to run in worktree mode. It SHALL:
- create `.env` from `.env.example`, turn on worktree mode and set `VIPTOP_DATA_DIR` to the shared data folder chosen as the requirement "Choose the shared data folder" describes;
- check the exports;
- start the stack and import the exports;
- print the stack information.

#### Scenario: Fresh worktree
- **WHEN** a checkout has no `.env`, Docker is reachable, no volumes exist for its Compose project and the shared data folder holds `sites_<digits>.csv`, `bins_<digits>.csv` and `bin_hist_<digits>.csv`
- **THEN** the skill leaves the checkout with a running stack on Docker-chosen ports, imported collection data and its URLs shown to the developer

#### Scenario: Derived tables after import
- **WHEN** the import reports derived tables it emptied, such as bin population or the bin-day calendar
- **THEN** the skill lists the refill commands and asks whether to run them

### Requirement: Choose the shared data folder
`worktree-setup` SHALL use the `data/` folder next to the checkout (in the checkout's parent folder) without asking when it holds `sites_<digits>.csv`, `bins_<digits>.csv` and `bin_hist_<digits>.csv`, and set `VIPTOP_DATA_DIR=../data`. Otherwise it SHALL ask the developer where the data folder is and use the folder they name.

#### Scenario: Data folder next to the worktree
- **WHEN** `<parent>/data/` holds all three collection exports
- **THEN** the skill sets `VIPTOP_DATA_DIR=../data` without asking

#### Scenario: No usable data folder next to the worktree
- **WHEN** `<parent>/data/` does not exist or lacks any of the three exports
- **THEN** the skill asks where the data folder is and checks the folder the developer names

### Requirement: Create a worktree and set it up
`worktree-create` SHALL create a git worktree for a branch the developer names. A new branch SHALL start from `main` unless the developer chooses another base. It SHALL place the worktree next to the existing worktrees, named after the branch, then run `worktree-setup` in it.

#### Scenario: New branch in a sibling layout
- **WHEN** existing worktrees are sibling folders of one parent, and the developer asks for new branch `route-preview`
- **THEN** the skill creates `<parent>/route-preview` on a new branch `route-preview` from `main`, then sets it up as `worktree-setup` does

### Requirement: Ask when something is unusual
Neither skill SHALL decide on its own in a non-routine situation. It SHALL describe what it found and wait for the developer's choice. The scenarios below list the situations that count as non-routine at a minimum.

#### Scenario: Existing environment file
- **WHEN** the checkout already has `.env`
- **THEN** the skill shows the lines it would add or change and edits nothing until the developer agrees

#### Scenario: Leftover volumes
- **WHEN** Docker volumes already exist for the checkout's Compose project name
- **THEN** the skill explains that they may hold another branch's database and asks whether to reuse them or remove them before starting

#### Scenario: Missing exports
- **WHEN** the folder the developer named lacks any of the three collection exports
- **THEN** the skill stops before starting the import and asks the developer to add the exports

#### Scenario: Several exports for one table
- **WHEN** the data folder holds more than one export for a table
- **THEN** the skill names the newest file the import will use and asks the developer to confirm

#### Scenario: Docker not reachable
- **WHEN** the Docker daemon cannot be reached
- **THEN** the skill reports the error and stops without changing Docker settings or permissions

#### Scenario: Explicit port already in use
- **WHEN** `.env` sets a port variable to a host port that is already taken
- **THEN** the skill names the port and the variable and asks whether to change or remove it before starting

#### Scenario: Existing folder or branch
- **WHEN** the target folder already exists, or the requested new branch already exists locally
- **THEN** `worktree-create` asks whether to use the existing branch, pick another name or stop

#### Scenario: Unusual worktree layout
- **WHEN** existing worktrees are not sibling folders of one parent
- **THEN** `worktree-create` asks where to put the new worktree

#### Scenario: Remote-only branch
- **WHEN** the requested branch exists on the remote but not locally
- **THEN** `worktree-create` asks whether to track the remote branch or create a new one

### Requirement: Never run the VASA synchronization
Neither skill SHALL run `bin_sync` to get development data.

#### Scenario: No exports available
- **WHEN** no CSV exports can be found
- **THEN** the skill asks the developer for exports and does not start a synchronization
