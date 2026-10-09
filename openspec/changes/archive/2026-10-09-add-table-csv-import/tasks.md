# Tasks

## 1. Repository setup

- [x] 1.1 Confirm that `backend/data/` stays git-ignored (root `.gitignore`), and add `data` to `backend/.dockerignore`. Verify that `git status --ignored backend/data` lists the folder as ignored and that `.dockerignore` contains the entry.

## 2. Import command

- [x] 2.1 Create `backend/app/interfaces/table_import/` with `__init__.py`, `__main__.py` (`raise SystemExit(main())`) and `cli.py` that follow the `bin_sync` CLI pattern: `argparse` with an optional `--dir`, which defaults to `backend/data` resolved from the module location; logging; and `Settings`/`create_database_engine`. Verify that `docker compose exec backend uv run python -m app.interfaces.table_import --help` prints the usage and exits 0.
- [x] 2.2 Implement file discovery over `Base.metadata.sorted_tables` with `^<table>_(\d+)\.csv$`, picking the highest suffix and warning about unmatched `*.csv` files. Exit 1 for a missing directory or no matches. Verify this with the current exports (it selects `sites`, `bins` and `bin_hist`), with an empty temporary directory (exit 1, nothing changed) and with `--dir /nonexistent` (exit 1).
- [x] 2.3 Implement the single-transaction load: `SET LOCAL lock_timeout`, then `TRUNCATE` the selected tables plus `vasa_import_runs`/`vasa_import_progress` when any of `sites`/`bins`/`bin_hist` is selected (no CASCADE), then `COPY ... FROM STDIN (FORMAT csv, HEADER true, NULL 'NULL')` per table in dependency order with header-derived quoted column lists, then `setval` on each identity sequence, then per-table row counts. Verify that importing the three current exports exits 0 and that the logged row counts match `SELECT count(*)` for each table (about 9.4k sites, 22k bins and 200k history rows).
- [x] 2.4 Map failures to readable log lines without credentials and exit 1, with the foreign-key truncate case adding the "referencing tables also need files" hint. Verify with a temporary directory that holds only a copy of `sites_*.csv`: it exits 1 with the hint, and the counts for `sites`, `bins` and `bin_hist` are unchanged.

## 3. Behaviour verification and documentation

- [x] 3.1 Write `docs/table-import-verification.md` with repeatable manual checks against disposable or local data, each with exact commands and expected results:
  - a full import and its counts
  - `trucks` unchanged (compare `SELECT count(*), max(id) FROM trucks` before and after)
  - preserved IDs (`SELECT site_id FROM bins WHERE id = 3` → 2)
  - NULL vs empty reason (`SELECT count(*) FROM bin_hist WHERE non_serviced_reason IS NULL` vs `= ''` matches the file)
  - the identity sequence advanced (insert a truck, or check `pg_get_serial_sequence` values above `max(id)`)
  - sync state cleared (`SELECT count(*) FROM vasa_import_runs` = 0)
  - rollback on a corrupted copy of `bin_hist` (all three tables keep their previous counts)
  - the newest file winning when two `bins_*` files exist
  - a rerun being idempotent

  Run each check and verify that it gives the documented result.
- [x] 3.2 Add a short "Import table CSV exports" section to `README.md`. It should cover the Docker and native commands, `--dir`, the file naming rule, the expected export settings (header row, unquoted `NULL`, UTF-8), the replace-only-present-tables behaviour, the clearing of sync progress, and the warning that the imported tables' current contents are discarded. Mention `table_import/` in the project-structure tree. Verify that the documented Docker command runs as written.
- [x] 3.3 Run `uv run python -m app.interfaces.bin_sync --max-sites 10` after an import. Verify that it starts a new pass without key conflicts and that new history or bin IDs, if any, are greater than the imported maxima.

## Workflow follow-up

- Archive the change with `/opsx:archive` after review, so that `table-csv-import` becomes a main spec.
