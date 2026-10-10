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
The command SHALL read CSV files from a directory given with `--dir`, otherwise from `VIPTOP_DATA_DIR` when set (relative values resolved from the repository root), otherwise from `backend/data/`. Inside the backend container, the default is the mounted data directory. A file SHALL be matched to a database table when its name is `<table>_<digits>.csv` and `<table>` is a table of the application schema. When several files match one table, the file whose digit suffix sorts highest SHALL be used. Files that match no table SHALL be ignored with a warning.

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

#### Scenario: Shared data directory when run natively
- **WHEN** the root `.env` sets `VIPTOP_DATA_DIR=../data` and the command runs natively without `--dir`
- **THEN** files are discovered only in the `data` folder next to the repository root

#### Scenario: Explicit directory beats the variable
- **WHEN** `VIPTOP_DATA_DIR` is set and the command is run with `--dir /some/path`
- **THEN** files are discovered only in `/some/path`

#### Scenario: Inside the container
- **WHEN** Compose mounts the folder named by `VIPTOP_DATA_DIR` as the backend's data directory and the command runs in the backend container without `--dir`
- **THEN** files are discovered in that mounted folder

### Requirement: Replace only tables that have a file
Each selected table's entire contents SHALL be replaced by the rows of its file. Tables without a matching file SHALL keep their contents unchanged. `service_zones.geojson` in the selected directory SHALL additionally select `service_zones` for replacement with the validated zone records, even when no CSV files are selected.

#### Scenario: Trucks survive a collection import
- **WHEN** files exist for `sites`, `bins` and `bin_hist` but not for `trucks`
- **THEN** after the import those three tables contain exactly the file rows and all truck rows are unchanged

#### Scenario: Previously stored rows are removed
- **WHEN** `bins` holds a row whose ID does not appear in the imported bins file
- **THEN** that row no longer exists after the import

#### Scenario: Zone source joins the collection import
- **WHEN** the selected directory contains collection CSVs and the supplied `service_zones.geojson`
- **THEN** the selected collection tables are replaced and `service_zones` contains the five imported zones
- **AND** unrelated tables retain the behavior defined by their existing import requirements

#### Scenario: Zone-only normal import
- **WHEN** the selected directory contains valid `service_zones.geojson` and no matching CSVs
- **THEN** the normal import succeeds and replaces only `service_zones`

### Requirement: All-or-nothing import
All selected tables SHALL be replaced together, or none SHALL be. Any failure, including malformed CSV, invalid service-zone GeoJSON, unknown columns, constraint violations or a lost connection, SHALL leave every table exactly as it was before the command. Zone replacement SHALL participate in the same transaction as CSV replacement and existing derived-table resets.

#### Scenario: Bad row in the last file
- **WHEN** `sites` and `bins` load successfully but a `bin_hist` row violates a constraint
- **THEN** `sites`, `bins` and `bin_hist` all keep their pre-import contents and the command exits with failure

#### Scenario: Invalid zone file with valid CSVs
- **WHEN** selected CSVs are valid but a present zone GeoJSON is invalid
- **THEN** the entire import fails and all selected tables, stored zones and derived tables remain unchanged

#### Scenario: CSV failure alongside valid zones
- **WHEN** the zone source is valid but a selected CSV fails during database loading
- **THEN** zones, CSV-selected tables and derived-table resets all retain their pre-import state

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
The command SHALL fail without changes when it would replace a table that another table without a file still references. Apart from the synchronization state and bin-day calendar resets described in this specification, tables that have no file are never emptied implicitly, except `bin_schedule`, which follows the requirement "Reset bin schedules with replaced bins".

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

### Requirement: Empty the bin-day calendar with replaced bins
When the import replaces `bins` and no `bin_days` file is selected, it SHALL also empty the derived bin-day calendar in the same transaction, so that no calendar row refers to a replaced bin. An import that does not replace `bins` SHALL keep the calendar.

#### Scenario: Collection import empties the calendar
- **WHEN** the calendar holds rows and files for `sites`, `bins` and `bin_hist` are imported
- **THEN** the import succeeds and the calendar is empty until it is rebuilt

#### Scenario: History-only import keeps the calendar
- **WHEN** only `bin_hist_*.csv` is present
- **THEN** the calendar rows are unchanged

### Requirement: Clear output and exit codes
The command SHALL report which file is used for each selected table, including service-zone GeoJSON, and its resulting row count. It SHALL exit with 0 on success. It SHALL exit with 1 when no CSV or zone source selects a table, the directory is missing, or the import fails, with a readable reason that does not disclose database credentials. A missing optional zone source alone SHALL NOT make an otherwise successful import fail.

#### Scenario: Successful run summary
- **WHEN** the three current exports are imported
- **THEN** the output lists each table with its source file and row count, and the exit code is 0

#### Scenario: Nothing to import
- **WHEN** the data directory has no matching CSV and no `service_zones.geojson`
- **THEN** the command changes nothing, says so, and exits with 1

#### Scenario: Missing directory
- **WHEN** `--dir` points to a directory that does not exist
- **THEN** the command changes nothing, reports the path, and exits with 1

#### Scenario: Report imported zones
- **WHEN** the supplied zone file is included in a successful normal import
- **THEN** output identifies `service_zones.geojson`, reports five rows for `service_zones` and exits with 0

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

### Requirement: Empty the resident allocation with replaced bins
When the import replaces `bins` and no `bin_population` file is selected, it SHALL empty the per-bin resident allocation in the same transaction, report that it did so and name `python -m app.interfaces.bin_population` as the command that refills it. Stored population polygons SHALL be kept. An import that does not replace `bins` SHALL keep the allocation.

#### Scenario: Collection import empties the allocation
- **WHEN** resident allocations are stored and files for `sites`, `bins` and `bin_hist` are imported
- **THEN** the import succeeds, no bin has a resident allocation, the population polygons are unchanged, and the output names the refill command

#### Scenario: History-only import keeps the allocation
- **WHEN** only `bin_hist_*.csv` is present
- **THEN** every bin keeps its resident allocation

### Requirement: Optional zone source in the selected directory
The normal command SHALL look for `service_zones.geojson` only in the directory resolved by its existing `--dir`, configured data-directory and container-mount rules. If the GeoJSON is missing, it SHALL warn and preserve stored zones unless a service-zone CSV explicitly selects that table. A present unreadable or invalid GeoJSON SHALL fail the import, rather than being skipped.

#### Scenario: Collection CSVs without zone data
- **WHEN** collection CSVs are present but no zone GeoJSON or service-zone CSV exists
- **THEN** collection import proceeds, output warns about the missing zone source and stored zones remain unchanged

#### Scenario: Explicit directory stays authoritative
- **WHEN** `--dir` points to a directory without zones while the default directory contains a zone GeoJSON
- **THEN** the default GeoJSON is not read and the missing-source warning identifies the selected directory

#### Scenario: Existing CSV restore remains available
- **WHEN** a service-zone CSV is selected and no zone GeoJSON is present
- **THEN** existing CSV restoration rules apply to that table
- **AND** output makes clear that the GeoJSON source is absent

### Requirement: Reject competing service-zone sources
If CSV discovery selects a `service_zones_<digits>.csv` while `service_zones.geojson` is also present, the normal command SHALL fail before replacing any tables and identify the competing sources. It SHALL NOT silently overwrite either source with the other.

#### Scenario: Both zone source formats present
- **WHEN** the selected directory contains zone GeoJSON and a matching service-zone CSV
- **THEN** the command exits with 1, names the conflict and leaves every table unchanged
