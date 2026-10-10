# Spec Delta

## MODIFIED Requirements

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
