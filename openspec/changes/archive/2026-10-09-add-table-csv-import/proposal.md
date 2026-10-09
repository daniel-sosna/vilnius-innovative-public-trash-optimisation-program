# Proposal

## Why

A full VASA synchronization takes a long time and depends on the external source. Teammates already have filled databases. They can export tables to CSV, but there is no easy way to load those exports into another developer's local database. A single import command lets every developer and the data analyst start from the same demo data in seconds.

## What Changes

- Add a manual backend command, `python -m app.interfaces.table_import`. It reads table CSV exports from `backend/data/` (or a directory given with `--dir`) and replaces the matching database tables.
- A file belongs to a table when its name is `<table>_<digits>.csv`, for example `bins_202610091935.csv`. If there are several files for one table, the newest timestamp wins. Tables that have no file stay untouched (for example, `trucks` in the current exports).
- The import is all-or-nothing. Every selected table is emptied and reloaded in one transaction, and exported `id`s are preserved so the relationships between the files stay intact. Any failure leaves the database unchanged.
- Importing any collection table (`sites`, `bins`, `bin_hist`) also clears the persisted VASA synchronization run and progress state. The next `bin_sync` invocation then starts a fresh pass and doesn't resume work that refers to replaced rows.
- After loading, the next generated `id` of each imported table continues after the highest imported `id`, so later inserts and syncs don't collide with it.
- `backend/data/` is excluded from git (already done) and from the backend Docker build context.
- **BREAKING** (for local data only): running the command discards the current contents of the imported tables. This is intended.

## Capabilities

### New Capabilities
- `table-csv-import`: a manual, all-or-nothing replacement of database tables from CSV exports. It covers file discovery, which tables are affected, data fidelity (preserved IDs, NULL vs empty text), referential safety, the reset of synchronization state, and command output and exit codes.

### Modified Capabilities
None. `bin-synchronization` behaviour is unchanged. After an import there is simply no run to resume, which the existing "refresh completed passes" path already handles as a fresh pass.

## Impact

- **Code**: a new `backend/app/interfaces/table_import/` CLI package next to `bin_sync`. It reuses `Settings`, `create_database_engine` and the ORM `Base.metadata`. There are no schema migrations and no new dependencies, because psycopg's `COPY` support is already installed.
- **Files**: `backend/.dockerignore` gains `data`. The README and a verification doc get a short section on the import.
- **Data**: the imported tables are fully replaced. Trucks and other tables without a file are not changed.
- **Assumptions**: the CSVs are exports of this project's own schema in the current DBeaver format. That means a header row with column names, unquoted `NULL` for null, quoted strings that may contain newlines, and `true`/`false` booleans. Other formats aren't supported.
- **Uncertainty**: a partial import where a referencing table has no file (for example only `sites_*.csv`) is rejected by PostgreSQL's foreign-key truncate check. The script doesn't add its own dependency analysis.
