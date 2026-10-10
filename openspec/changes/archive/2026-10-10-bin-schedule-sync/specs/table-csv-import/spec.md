# Spec Delta

## MODIFIED Requirements

### Requirement: Reject imports that would break references
The command SHALL fail without changes when it would replace a table that another table without a file still references. Tables that have no file are never emptied implicitly, except `bin_schedule`, which follows the requirement "Reset bin schedules with replaced bins".

#### Scenario: Sites without dependents
- **WHEN** only `sites_*.csv` is present and stored bins reference sites
- **THEN** the command exits with failure and says that the referencing tables also need files
- **AND** `sites`, `bins` and `bin_hist` are unchanged

#### Scenario: Leaf table alone
- **WHEN** only `bin_hist_*.csv` is present and all its `bin_id`s exist in stored bins
- **THEN** only `bin_hist` is replaced

## ADDED Requirements

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
