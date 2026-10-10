# Proposal

## Why

`bin_days` is the input contract for the synthetic fill-level generator, but its columns are only partly explained. The README table groups six copied bin attributes into one row ("Copied from `bins`"), defines `resident_factor` in another section, and gives no types, nullability, units or keys. The developer writing the generator and the data analyst need one place that explains every column before they build on it.

## What Changes

- Add `docs/bin-days-columns.md`, a data dictionary with one entry per `bin_days` column: SQL type, nullability, data kind (calendar, registry snapshot, estimated, synthetic), source, meaning, units or allowed values, and notes for the generator. It also states the row grain and the primary key.
- Move the column table and the `collection_status` value list from the README "Bin-day calendar" section into that file, and replace them with a link. The README keeps how to run the rebuild and the simulation assumptions.
- Point the `BinDay` model docstring to the new file, so whoever adds a column knows where to document it.

No schema, behaviour or command output changes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This is documentation only: no spec-level behaviour changes, so the change sets `skip_specs: true`.

## Impact

- New: `docs/bin-days-columns.md`.
- Edited: `README.md` (Bin-day calendar section), `backend/app/infrastructure/models.py` (docstring only).
- Both edited files have uncommitted changes from the bin-population work in this worktree. This change builds on that state, which already includes `population_cell_id` and `resident_factor`.
- Assumption: the allowed values listed for `waste_type` and `object_group` come from the current exports (`bins_202610091935.csv`). They are observed values, not enforced constraints, and the doc will say so.
