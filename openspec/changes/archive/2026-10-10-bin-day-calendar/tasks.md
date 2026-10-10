# Tasks

## 1. Schema

- [x] 1.1 Add migration `backend/alembic/versions/0005_bin_days.py` (revises `0004`). It creates `bin_days` with the columns, CHECK constraints, primary key `(bin_id, date)` and `ON DELETE CASCADE` foreign key to `bins` from design D1, and its downgrade drops the table. Verify:
  - run `docker compose exec backend uv run alembic upgrade head`, then `downgrade 0004` and `upgrade head` again, and check that both succeed
  - `\d bin_days` in psql shows the expected columns and constraints
- [x] 1.2 Add the `BinDay` ORM model to `backend/app/infrastructure/models.py`, matching the migration. Verify that `uv run alembic check` (or autogenerate in a scratch run) reports no differences between the models and the migrated schema.

## 2. Keep the CSV import working

- [x] 2.1 In `backend/app/interfaces/table_import/cli.py`, add `bin_days` to the `TRUNCATE` set when `bins` is selected and `bin_days` is not (design D3), and log that the bin-day calendar was emptied and must be rebuilt. Verify:
  - with a non-empty `bin_days`, the full collection import exits with 0 and leaves `bin_days` empty
  - a `bin_hist`-only import leaves `bin_days` unchanged
- [x] 2.2 Update the README "Import table CSV exports" section and `docs/table-import-verification.md` (add a check for both cases above). Verify that the documented commands run as written.

## 3. Rebuild command

- [x] 3.1 Create the `backend/app/interfaces/bin_days/` package (`__init__.py`, `__main__.py`, `cli.py`) with required `--start` and `--end` ISO dates. Map argparse errors to exit code 1, reject a reversed range and a range over 1,827 days before connecting, and keep error messages free of credentials. Verify:
  - a missing argument, `--start 2026-13-01`, a reversed range and `--start 2026-09-09 --end 2031-09-10` (1,828 days) each exit with 1 and change nothing
  - `--start 2027-03-01 --end 2032-02-29` (1,827 days) passes validation
  - `--help` exits with 0
- [x] 3.2 Implement the rebuild: `TRUNCATE` and one `INSERT ... SELECT` over `generate_series x bins WHERE sub_district IS NOT NULL` in one transaction with `lock_timeout` (design D2), then log the range, the day count, included and excluded bins and total rows. Verify that `python -m app.interfaces.bin_days --start 2026-09-09 --end 2026-10-09` exits with 0 and reports 31 days, 21,804 included and 147 excluded bins, and 675,924 rows.

## 4. Documentation and verification

- [x] 4.1 Write `docs/bin-day-calendar-verification.md` with repeatable psql checks against the spec scenarios. Verify by running every check against the imported data:
  - row count = included bins x days, and no duplicates per `(bin_id, date)`
  - no bin with a NULL `sub_district` appears, and bins with a NULL `object_group` do appear
  - 2026-10-09 has dow 5, week 41, month 10 and season 4
  - a one-day rebuild for 2026-12-01 gives season 1, and one for 2027-01-01 gives week 53 and dow 5
  - attributes of bin 3 match `bins`
  - a narrower rebuild removes dates outside the new range
  - emptying `bin_hist` in a transaction and rebuilding yields identical contents (then roll back)
  - deleting one bin in a rolled-back transaction removes its rows
- [x] 4.2 Add a "Bin-day calendar" section to the README covering:
  - purpose, columns and season numbering
  - the command, with the 2026-09-09..2026-10-09 example
  - the snapshot and ISO-week caveats
  - that a collection import empties the table
  - a link to the verification doc

  Verify that the README commands run as written.

## 5. End-to-end check

- [x] 5.1 On a fresh `docker compose up --build`, run `table_import` and then the rebuild command, then run every check in `docs/bin-day-calendar-verification.md` and the two import checks from 2.2. Confirm that all pass, then run `openspec validate bin-day-calendar --strict`.
