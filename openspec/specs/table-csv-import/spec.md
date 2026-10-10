# table-csv-import Specification

## Purpose

Lets a developer replace local database tables with CSV exports of the same schema, using one manual command, so the team can share the same collection data without running a full VASA synchronization.

## Requirements

### Requirement: Import only on explicit invocation
Table import SHALL run only when an operator invokes the import command. It SHALL work both inside the backend container and natively, using the existing database configuration. Application startup, migrations and idle runtime SHALL NOT import CSV files.

#### Scenario: Startup ignores exports
- **WHEN** CSV exports are present in the data directory and the backend starts
- **THEN** no table contents change until the import command is run

### Requirement: Discover export files by table name
The command SHALL read CSV files from `backend/data/` by default, or from a directory given with `--dir`. A file SHALL be matched to a database table when its name is `<table>_<digits>.csv` and `<table>` is a table of the application schema. When several files match one table, the file whose digit suffix sorts highest SHALL be used. Files that match no table SHALL be ignored with a warning.

#### Scenario: Default directory with current exports
- **WHEN** the data directory contains `sites_202610092000.csv`, `bins_202610091935.csv` and `bin_hist_202610091935.csv`
- **THEN** the command selects the `sites`, `bins` and `bin_hist` tables, each with its file

#### Scenario: Newest export wins
- **WHEN** the data directory contains `bins_202610010000.csv` and `bins_202610091935.csv`
- **THEN** only `bins_202610091935.csv` is imported into `bins`

#### Scenario: Prefixes do not collide
- **WHEN** the data directory contains `bin_hist_202610091935.csv` and no `bins_*.csv`
- **THEN** only `bin_hist` is selected

#### Scenario: Unknown file
- **WHEN** the data directory contains `notes.csv` or `routes_backup_202610091935.csv` that names no schema table
- **THEN** the file is reported as ignored and does not affect the import

#### Scenario: Custom directory
- **WHEN** the command is run with `--dir /some/path`
- **THEN** files are discovered only in `/some/path`

### Requirement: Replace only tables that have a file
Each selected table's entire contents SHALL be replaced by the rows of its file. Tables without a matching file SHALL keep their contents unchanged.

#### Scenario: Trucks survive a collection import
- **WHEN** files exist for `sites`, `bins` and `bin_hist` but not for `trucks`
- **THEN** after the import those three tables contain exactly the file rows and all truck rows are unchanged

#### Scenario: Previously stored rows are removed
- **WHEN** `bins` holds a row whose ID does not appear in the imported bins file
- **THEN** that row no longer exists after the import

### Requirement: All-or-nothing import
All selected tables SHALL be replaced together, or none SHALL be. Any failure, including malformed CSV, unknown columns, constraint violations or a lost connection, SHALL leave every table exactly as it was before the command.

#### Scenario: Bad row in the last file
- **WHEN** `sites` and `bins` load successfully but a `bin_hist` row violates a constraint
- **THEN** `sites`, `bins` and `bin_hist` all keep their pre-import contents and the command exits with failure

### Requirement: Faithful reproduction of exported rows
Imported rows SHALL keep their exported `id` values and every column value from the file. Columns are matched by the header row, not by position. An unquoted `NULL` SHALL be stored as NULL, and a quoted empty string SHALL be stored as empty text. Quoted values may contain commas and line breaks.

#### Scenario: Identifiers and references preserved
- **WHEN** the bins file has a row with `id` 3 and `site_id` 2
- **THEN** after the import, bin 3 exists and belongs to site 2 as exported

#### Scenario: NULL versus empty reason
- **WHEN** one history row has `non_serviced_reason` `""` and another has `NULL`
- **THEN** the first is stored as empty text and the second as NULL

#### Scenario: Multi-line text value
- **WHEN** a quoted `non_serviced_reason` contains a line break
- **THEN** it is stored as one value with that line break, in one row

### Requirement: New records continue after imported identifiers
After an import, the next generated identifier of each imported table SHALL be greater than the highest imported `id`. For an empty imported file, it SHALL restart from the beginning.

#### Scenario: Synchronization after import
- **WHEN** bins with IDs up to 21950 are imported and a later process inserts a new bin
- **THEN** the new bin gets an ID greater than 21950 without a key conflict

### Requirement: Reject imports that would break references
The command SHALL fail without changes when it would replace a table that another table without a file still references. Tables that have no file are never emptied implicitly, except `bin_schedule`, which follows the requirement "Reset bin schedules with replaced bins".

#### Scenario: Sites without dependents
- **WHEN** only `sites_*.csv` is present and stored bins reference sites
- **THEN** the command exits with failure and says that the referencing tables also need files
- **AND** `sites`, `bins` and `bin_hist` are unchanged

#### Scenario: Leaf table alone
- **WHEN** only `bin_hist_*.csv` is present and all its `bin_id`s exist in stored bins
- **THEN** only `bin_hist` is replaced

### Requirement: Reset synchronization progress with collection data
When the import replaces `sites`, `bins` or `bin_hist`, it SHALL also discard all persisted VASA synchronization runs and progress in the same transaction. The next synchronization then starts a fresh pass. An import of other tables only SHALL keep the synchronization state.

#### Scenario: Collection import discards an incomplete pass
- **WHEN** an incomplete VASA synchronization pass exists and collection tables are imported
- **THEN** no synchronization run remains, and the next sync invocation starts a new pass

#### Scenario: Truck-only import keeps sync state
- **WHEN** only `trucks_*.csv` is present
- **THEN** stored synchronization runs and progress are unchanged

### Requirement: Clear output and exit codes
The command SHALL report which file is used for each table and how many rows each table contains after the import. It SHALL exit with 0 on success. It SHALL exit with 1 when there is nothing to import, the directory is missing, or the import fails, with a readable reason that doesn't disclose database credentials.

#### Scenario: Successful run summary
- **WHEN** the three current exports are imported
- **THEN** the output lists each table with its source file and row count, and the exit code is 0

#### Scenario: Nothing to import
- **WHEN** the data directory has no file that matches a schema table
- **THEN** the command changes nothing, says so, and exits with 1

#### Scenario: Missing directory
- **WHEN** `--dir` points to a directory that does not exist
- **THEN** the command changes nothing, reports the path, and exits with 1

### Requirement: Reset bin schedules with replaced bins
When the import replaces `bins` and there is no `bin_schedule` file, it SHALL empty `bin_schedule` in the same transaction and report that it did so. When a `bin_schedule` file is present, that table SHALL be replaced from the file like any other table. Imports that do not replace `bins` SHALL keep `bin_schedule` unchanged.

#### Scenario: Current collection exports without a schedule file
- **WHEN** the data directory has `sites`, `bins` and `bin_hist` exports but no `bin_schedule` export, and planned dates are stored
- **THEN** the import succeeds, `bin_schedule` is empty, and the output says the schedules were cleared

#### Scenario: Schedule export included
- **WHEN** the data directory also contains `bin_schedule_202610101200.csv`
- **THEN** `bin_schedule` contains exactly the rows of that file

#### Scenario: History-only import keeps schedules
- **WHEN** only `bin_hist_*.csv` is present
- **THEN** stored planned dates are unchanged
