# Design

## Context

See `proposal.md` for the motivation and `specs/table-csv-import/spec.md` for the required behaviour.

Current state that shapes the approach:

- The schema is defined in `backend/app/infrastructure/models.py` (`Base.metadata`) and managed by Alembic. All `id` columns are `GENERATED ALWAYS AS IDENTITY`. `bins.site_id` references `sites` with `ON DELETE RESTRICT`, `bin_hist.bin_id` references `bins` with `CASCADE`, and `vasa_import_progress.run_id` references `vasa_import_runs`.
- The only existing CLI is `app.interfaces.bin_sync` (`argparse`, `Settings()`, `create_database_engine`, logging, integer exit code). It runs the same way in Docker (`docker compose exec backend uv run python -m ...`) and natively.
- Compose bind-mounts `./backend` at `/app`, so `backend/data/` is already visible in the container as `/app/data/`.
- Observed export format (DBeaver): UTF-8 without a BOM, a quoted header row, unquoted `NULL` for null, `""` for empty text, multi-line quoted values in `bin_hist.non_serviced_reason`, `true`/`false` booleans, and `YYYY-MM-DD HH:MM:SS.mmm` timestamps. Current sizes are about 9.4k sites, 22k bins and 200k history rows (15 MB).
- PostgreSQL 17 (`postgres:17-alpine`). psycopg 3 is already a dependency.

## Goals / Non-Goals

**Goals:**
- One short command with no required arguments. It finishes in seconds for the current data.
- About one small module, with no new dependencies, migrations or service layers.

**Non-Goals:**
- Merging or upserting into existing rows. Imports always replace whole tables.
- Supporting CSV dialects other than the observed export format, or files whose columns differ from the schema.
- Exporting tables. Teammates keep using DBeaver or `psql \copy` for that.
- Importing tables outside `Base.metadata` (for example `alembic_version`).
- Automated tests. These are excluded by project policy, and a manual verification doc replaces them.

## Decisions

### 1. A CLI package next to `bin_sync`, not a root `scripts/` file
`backend/app/interfaces/table_import/` (`__main__.py` and `cli.py`) mirrors `bin_sync`. It reuses `Settings` and `create_database_engine`, so the database URL, dotenv loading and credential hiding behave identically. It's also available in the container without new mounts.
*Alternative*: `scripts/import_csv.py` at the repo root. That directory isn't mounted into the backend container, and the script would need its own config handling.
*Note*: `Settings` also requires `BIN_SYNC_HTTP_TIMEOUT_SECONDS`. It is already present in Compose and `.env`, so this is accepted rather than splitting the settings.

### 2. Discover tables from `Base.metadata`
`Base.metadata.sorted_tables` gives the schema's table names in foreign-key dependency order (parents first). For each table, the command looks for files matching `^<table>_(\d+)\.csv$` and takes the highest suffix. Comparing suffixes as strings works because they're fixed-width timestamps. The anchored regex keeps `bins_*` and `bin_hist_*` apart. New tables become importable automatically.
*Alternative*: a hardcoded list of three tables. It's no simpler, and it would block importing `trucks` later.

### 3. Load with PostgreSQL `COPY ... FROM STDIN` in one transaction
The command opens one `engine.begin()` transaction, takes the raw psycopg connection, and does the following:

1. `SET LOCAL lock_timeout`, reusing `SYNC_LOCK_TIMEOUT_MS`, so a busy server can't make the command hang forever.
2. `TRUNCATE <selected tables> [, vasa_import_runs, vasa_import_progress]`, in one statement and without `CASCADE`.
3. For each selected table in `sorted_tables` order, read the header with the `csv` module to get the column list. Then run `COPY <table> (<cols>) FROM STDIN WITH (FORMAT csv, HEADER true, NULL 'NULL')` and stream the file through `cursor.copy()`. Identifiers are quoted with `psycopg.sql.Identifier`.
4. For each selected table, run `setval(pg_get_serial_sequence('<table>', 'id'), COALESCE(MAX(id), 0) + 1, false)`.
5. Count the rows for the summary, then commit.

Why COPY: PostgreSQL's CSV parser already handles quoted newlines, `""` vs unquoted `NULL`, booleans and timestamps. `COPY FROM` writes the provided values into `GENERATED ALWAYS` identity columns (the equivalent of `OVERRIDING SYSTEM VALUE`), so IDs are preserved without schema tricks. It loads 200k rows in about a second.
*Alternative*: ORM or `executemany` inserts. They need type conversion per column, explicit `OVERRIDING SYSTEM VALUE` and NULL/empty handling, and they're orders of magnitude slower.

### 4. Let PostgreSQL enforce referential safety
A plain `TRUNCATE` (RESTRICT) of a table that a non-truncated table references fails with `FeatureNotSupported` ("cannot truncate a table referenced in a foreign key constraint"). The CLI catches this case and logs a short hint, "files for the referencing tables are also required", along with PostgreSQL's message, which names the tables. Rows loaded by COPY also go through the normal FK and check constraints, so inconsistent files fail the whole transaction.
*Alternatives*: `TRUNCATE ... CASCADE` would silently empty tables that have no file, which violates the spec. A custom dependency check would duplicate what PostgreSQL already does.

### 5. Truncate the sync state with the collection tables
If the selected set intersects `{sites, bins, bin_hist}`, `vasa_import_runs` and `vasa_import_progress` are added to the same TRUNCATE. This needs no special code path in `bin_sync`. With no run present, it starts a fresh pass.

### 6. Output and exit codes
The output style follows `bin_sync`: `logging` at INFO, one line per table (`bins <- bins_202610091935.csv: 21950 rows`), a warning for each ignored `*.csv`, and errors reduced to the exception type plus PostgreSQL's message, with no connection URL. The command returns 0 on success. It returns 1 for a missing directory, no matching files, or any database or file error, all before or with a rollback.

## Risks / Trade-offs

- [A teammate's export comes from an older schema, with a missing or extra column] → An extra column makes COPY fail and the import rolls back. A missing nullable column loads as NULL. The error names the column. Teammates should export after running the same migrations.
- [The export format changes, for example a different NULL marker, or a DBeaver setting quoting `NULL`] → The data loads wrong or fails. The README documents the expected export settings.
- [Running the import while `bin_sync` or the API holds locks] → `lock_timeout` makes it fail fast with exit code 1, and the user can retry.
- [Accidentally wiping local data that was synced since the snapshot] → This is accepted. The command is explicit and local-only, and the README warns that it replaces the tables.
- [The `Settings` coupling to the sync timeout variable] → This is accepted for now. It's already required everywhere the backend runs.

## Migration Plan

There are no schema migrations. Rollback means removing the package. Data rollback isn't possible after a successful import, beyond re-running `bin_sync` or importing older files.
