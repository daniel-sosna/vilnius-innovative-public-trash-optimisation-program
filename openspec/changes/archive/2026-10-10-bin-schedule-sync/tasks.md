# Tasks

Prerequisite for verification: `backend/data/` contains `sites_<digits>.csv`, `bins_<digits>.csv` and `bin_hist_<digits>.csv`. If any is missing, ask the developer for the exports. Never use `bin_sync` to get data.

## 1. Schema

- [x] 1.1 Add the `BinSchedule` model to `app/infrastructure/models.py` (`id` identity, `bin_id` FK to `bins.id` `ON DELETE CASCADE`, `date DATE`, unique `(bin_id, date)`, index on `date`) and add a `schedule` relationship on `Bin` with `passive_deletes`. Verify: `python -c "from app.infrastructure.models import Base; print('bin_schedule' in Base.metadata.tables)"` prints `True`.
- [x] 1.2 Add Alembic migration `0005_bin_schedule.py` (down_revision `0004`) in the explicit-SQL style of `0004`, with a downgrade that drops the table. Verify: `uv run alembic upgrade head`, `\d bin_schedule` shows the FK, unique constraint and index, then `alembic downgrade 0004` and `upgrade head` both succeed.

## 2. CSV import keeps working

- [x] 2.1 In `app/interfaces/table_import/cli.py`, add `bin_schedule` to the `TRUNCATE` list when `bins` has a file and `bin_schedule` does not, and log that schedules were cleared. Verify: with the current three exports in `backend/data/`, `uv run python -m app.interfaces.table_import` exits 0 and its output mentions the cleared schedules.
- [x] 2.2 Update the README section "Import table CSV exports" (the Replacement bullet) to describe the `bin_schedule` reset and the optional `bin_schedule_<digits>.csv`. Verify by reading it back against the modified `table-csv-import` spec.

## 3. VASA schedule client

- [x] 3.1 Add `vasa_schedule_url_template` to `Settings` with the public default and include it in the `{external_id}` HTTPS validator. Verify: `Settings()` loads with the default, and setting `VASA_SCHEDULE_URL_TEMPLATE=http://x/{external_id}` is rejected.
- [x] 3.2 Add `parse_schedule(payload)` and `VasaClient.schedule(identity)` to `app/integrations/vasa.py`. They return sorted distinct `date`s and raise `VasaError` on a non-object payload, missing or non-list `schedule`, or any non-ISO `YYYY-MM-DD` entry. Verify with a one-off `uv run python -c` call: `schedule(135353)` returns current-month dates, `schedule(999999999)` returns `[]`, and `parse_schedule({"schedule": ["07/10/2026"]})` raises.

## 4. Schedule command

- [x] 4.1 Create `app/services/bin_schedule_sync.py`. It loads `(id, external_id)` from `bins` ordered by id with an optional limit, fetches through `bounded_responses()` on a `ThreadPoolExecutor(workers)`, and replaces each bin's rows in its own `transaction()` (delete, then multi-row insert). A fetch or write failure is recorded per bin and the run continues. It returns counts: processed, with dates, empty, failed (with external IDs), dates stored.
- [x] 4.2 Create `app/interfaces/bin_schedule_sync/` (`__init__.py`, `__main__.py`, `cli.py`) following `bin_sync/cli.py`: `--workers` (default 4, >0) and `--max-bins` (default 0, >=0) validated before any request, logging, summary printing (failed IDs capped at the first 20), exit codes as in `bin_sync` (0 full success; 1 any failure, invalid input or an empty `bins` table with the message "import collection data first"; 2 a nonzero `--max-bins` run without failures). Errors must not disclose credentials. Verify: `uv run python -m app.interfaces.bin_schedule_sync --workers 0` exits 1 without requests, and `--max-bins 20` exits 2 with 20 bins processed and rows for those bins in `bin_schedule`.
- [x] 4.3 Add a "Collection schedules" README section: the command, its options and exit codes, the current-month snapshot behaviour, that an empty list can mean an unknown bin, the advice to re-run at the start of each month, and the approximate full-run duration. Also add `bin_schedule_sync/` to the project-structure comment. Verify by running the documented commands as written.

## 5. End-to-end verification

- [x] 5.1 Run `uv run python -m app.interfaces.bin_schedule_sync --max-bins 50` twice (each exits 2). The second run leaves the same row count, and `SELECT bin_id, count(*) FROM bin_schedule GROUP BY 1` shows one row per date with no duplicates. Then delete one of those bins in a transaction you roll back (`BEGIN; DELETE FROM bins WHERE id = <id>; SELECT count(*) FROM bin_schedule WHERE bin_id = <id>; ROLLBACK;`) and check that the count is 0 before the rollback.
- [x] 5.2 Re-run `uv run python -m app.interfaces.table_import` with the three exports. It exits 0 and `bin_schedule` is empty. Then run a full `uv run python -m app.interfaces.bin_schedule_sync` (expect exit 0) and record its duration and summary (bins, empty, failed) in the change's design.md Risks section or in the PR description.

## Workflow follow-up

- Archive the change with `/opsx:archive` after review, so `collection-schedules` becomes a main spec and the `table-csv-import` delta is merged.
