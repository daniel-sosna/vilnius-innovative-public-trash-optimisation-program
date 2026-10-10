# Design

## Context

Column information for `bin_days` lives in four places: the README table (`README.md`, "Bin-day calendar"), the `bin-day-calendar` spec (normative, spread over many requirements), the `BinDay` model in `backend/app/infrastructure/models.py`, and migrations `0008`, `0011` and `0012`. None of them explains every column on its own. See proposal.md for why that matters now.

## Goals / Non-Goals

**Goals:**
- One file that explains every `bin_days` column and that a reader can use without opening the code.
- No second copy of the column descriptions in the README.

**Non-Goals:**
- Database column comments (`COMMENT ON COLUMN`). They need a migration, and the analyst reads the repository.
- Data dictionaries for other tables (`bins`, `bin_population`, `population_cells`).
- Changing the spec. It stays the behaviour contract, and the doc describes the same columns in reader-facing terms.

## Decisions

**Dedicated file `docs/bin-days-columns.md` instead of expanding the README table.**
The README section is already about 80 lines of run instructions and assumptions. A per-column entry with type, null, kind, source, meaning and values would roughly double it. A separate file can be linked from the generator code and from discussions, and it can grow when the generator adds columns. Alternative: expand the README table in place. That keeps everything in one place, but it makes the README harder to scan, and per-column notes don't fit in a table cell.

**The README links to the file instead of keeping its table.**
The column table and the `collection_status` value list move out of the README, so each column is described in only one place. The README keeps the rebuild command, the options, eligibility, replacement and the assumptions, because those describe the rebuild, not individual columns. The file links back to those README parts instead of repeating them.

**Entry layout.**
- A summary table with these columns: name, SQL type, null, kind. Kind is one of `key`, `calendar`, `registry snapshot`, `estimated` or `synthetic`.
- Then one short section per column covering meaning, source, units or values, and how the generator should use it.
- The six copied bin attributes each get their own entry. Each entry gives the column's real-world meaning: `site_id` is the collection site, `sub_district` is the seniūnija, `object_group` is the client type, and the `capacity_m3` entry says the m³ unit is unverified.

The kind labels follow the project's distinction between observed, synthetic, estimated and assumed data.

**Observed value lists are labelled as such.**
`waste_type` (3 values) and `object_group` (10 values plus NULL) are listed with counts from the current export and dated. The database does not enforce them, so the doc says they can change with new exports. The `collection_status` values are enforced by a check constraint and are listed as the complete set.

**Keeping it current.**
The `BinDay` docstring names the file. The verification step compares the documented column names with `information_schema.columns` for `bin_days`.

## Risks / Trade-offs

- [Doc drifts from the schema when a column is added] → The model docstring points to the file, and the verification query compares column names.
- [Doc and spec disagree] → The doc defers to the spec for exact behaviour. It links to the `bin-day-calendar` spec and does not restate edge-case rules such as retry chains.
- [Edits overlap the uncommitted bin-population changes in README and models.py] → Apply this change on top of that work in this worktree, not on a fresh branch from `main`.
