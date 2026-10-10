# Spec Delta

## MODIFIED Requirements

### Requirement: Replace only tables that have a file
Each selected table's entire contents SHALL be replaced by the rows of its file. Tables without a matching CSV SHALL keep their contents unchanged, except `district_boundaries` when the selected directory contains `vilnius_seniuniju_ribos.geojson`; that table SHALL be replaced from the validated district source.

#### Scenario: Trucks survive a collection import
- **WHEN** files exist for `sites`, `bins` and `bin_hist` but not for `trucks`
- **THEN** after the import those three tables contain exactly the file rows and all truck rows are unchanged

#### Scenario: Previously stored rows are removed
- **WHEN** `bins` holds a row whose ID does not appear in the imported bins file
- **THEN** that row no longer exists after the import

#### Scenario: Replace districts alongside collection exports
- **WHEN** valid collection CSV exports and the district GeoJSON are present in the selected directory
- **THEN** selected collection tables and the district catalog are replaced together
- **AND** unrelated tables retain their existing behavior

#### Scenario: Preserve districts without an input
- **WHEN** collection exports are imported and neither a district GeoJSON nor a district CSV export is present
- **THEN** stored district boundaries remain unchanged


### Requirement: All-or-nothing import
All selected CSV tables and any selected district GeoJSON replacement SHALL be committed together, or none SHALL be. Any failure, including malformed CSV or GeoJSON, unknown columns, constraint violations or a lost connection, SHALL leave every table exactly as it was before the command.

#### Scenario: Bad row in the last file
- **WHEN** `sites` and `bins` load successfully but a `bin_hist` row violates a constraint
- **THEN** `sites`, `bins` and `bin_hist` all keep their pre-import contents and the command exits with failure

#### Scenario: Invalid district source alongside valid CSVs
- **WHEN** CSV inputs are valid but the present district source is invalid
- **THEN** no CSV or district table changes and the command exits with failure

#### Scenario: CSV failure after valid district validation
- **WHEN** district input is valid but a selected CSV cannot be imported
- **THEN** the previous district catalog and every selected CSV table remain unchanged


### Requirement: Clear output and exit codes
The command SHALL report each imported table's source file and resulting row count, including district GeoJSON input. It SHALL warn when the optional district source is missing. It SHALL exit with 0 on successful CSV and/or district import, and with 1 when neither input is available, the directory is missing, or the import fails, with a readable reason that doesn't disclose database credentials.

#### Scenario: Successful run summary
- **WHEN** the three current exports are imported
- **THEN** the output lists each table with its source file and row count, and the exit code is 0

#### Scenario: Nothing to import
- **WHEN** the data directory has no matching CSV export and no district GeoJSON
- **THEN** the command changes nothing, says so, and exits with 1

#### Scenario: Missing directory
- **WHEN** `--dir` points to a directory that does not exist
- **THEN** the command changes nothing, reports the path, and exits with 1

#### Scenario: District source without CSV exports
- **WHEN** the selected directory contains a valid district GeoJSON and no matching CSV exports
- **THEN** only the district catalog is replaced, its source and count are reported, and the command exits with 0

#### Scenario: Missing optional source during successful CSV import
- **WHEN** CSV exports import successfully and the district GeoJSON is absent
- **THEN** output warns that the optional source is missing and the command still exits with 0

## ADDED Requirements

### Requirement: Discover optional district GeoJSON in the selected directory
The regular table-import command SHALL discover `vilnius_seniuniju_ribos.geojson` in the same directory selected for CSV exports. A missing optional source SHALL warn and allow CSV import to proceed; an unreadable or invalid present source SHALL fail the import. Stored boundaries SHALL be preserved when neither district input is present.

#### Scenario: Explicit directory selects all import sources
- **WHEN** `--dir /some/path` selects a directory containing collection exports and the district source
- **THEN** both kinds of input are discovered there without looking in another directory

#### Scenario: Configured shared directory
- **WHEN** the default data-directory configuration selects a shared directory
- **THEN** the regular import looks for the district source in that directory alongside CSV exports

#### Scenario: Missing optional source
- **WHEN** the selected directory has valid CSV exports but no district GeoJSON or district CSV
- **THEN** CSV imports proceed, a warning identifies the missing district source, and the stored catalog is preserved

### Requirement: Reject competing district import inputs
If both the district GeoJSON and a selected `district_boundaries_<digits>.csv` export are present, the regular import SHALL fail before changing data and identify the conflicting paths. With only a district CSV export, existing CSV selection and replacement semantics SHALL apply.

#### Scenario: Two sources for one district table
- **WHEN** both district input forms are discovered
- **THEN** the command exits with 1, reports the conflict and changes no tables

#### Scenario: Restore a district table export
- **WHEN** a valid district CSV export is selected and no district GeoJSON is present
- **THEN** the district table is replaced from that CSV using the normal export rules

