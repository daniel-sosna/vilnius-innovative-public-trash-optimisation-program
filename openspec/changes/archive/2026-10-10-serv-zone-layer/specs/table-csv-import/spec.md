# Spec Delta

## MODIFIED Requirements

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

## ADDED Requirements

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
