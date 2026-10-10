# Spec Delta

## ADDED Requirements

### Requirement: Empty the bin-day calendar with replaced bins
When the import replaces `bins` and no `bin_days` file is selected, it SHALL also empty the derived bin-day calendar in the same transaction, so that no calendar row refers to a replaced bin. An import that does not replace `bins` SHALL keep the calendar.

#### Scenario: Collection import empties the calendar
- **WHEN** the calendar holds rows and files for `sites`, `bins` and `bin_hist` are imported
- **THEN** the import succeeds and the calendar is empty until it is rebuilt

#### Scenario: History-only import keeps the calendar
- **WHEN** only `bin_hist_*.csv` is present
- **THEN** the calendar rows are unchanged

## MODIFIED Requirements

### Requirement: Reject imports that would break references
The command SHALL fail without changes when it would replace a table that another table without a file still references. Apart from the synchronization state and bin-day calendar resets described in this specification, tables that have no file are never emptied implicitly.

#### Scenario: Sites without dependents
- **WHEN** only `sites_*.csv` is present and stored bins reference sites
- **THEN** the command exits with failure and says that the referencing tables also need files
- **AND** `sites`, `bins` and `bin_hist` are unchanged

#### Scenario: Leaf table alone
- **WHEN** only `bin_hist_*.csv` is present and all its `bin_id`s exist in stored bins
- **THEN** only `bin_hist` is replaced
