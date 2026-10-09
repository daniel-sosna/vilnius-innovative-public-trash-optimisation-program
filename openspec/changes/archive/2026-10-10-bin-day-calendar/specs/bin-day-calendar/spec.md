# Spec Delta

## Purpose

Provides a stored grid of every eligible bin on every day of an operator-chosen date range, with calendar features and bin attributes, as the input contract for synthetic fill-level generation.

## ADDED Requirements

### Requirement: Rebuild only on explicit invocation
The bin-day calendar SHALL change only when an operator runs the rebuild command with a start date and an end date. The command SHALL work inside the backend container and natively, using the existing database configuration. Application startup, migrations and idle runtime SHALL NOT build or change it.

#### Scenario: Startup leaves the calendar alone
- **WHEN** the backend starts or migrations run
- **THEN** the bin-day calendar contents are unchanged

#### Scenario: Both dates are required
- **WHEN** the command is run without `--start` or without `--end`
- **THEN** it changes nothing, explains the missing argument and exits with 1

### Requirement: One row per eligible bin per day
After a rebuild for `--start S --end E`, the calendar SHALL contain exactly one row for each eligible bin and each date from S to E inclusive, and no other rows. A bin is eligible when its `sub_district` is not NULL. Every eligible bin SHALL appear on every date, whatever its service history.

#### Scenario: Current history period
- **WHEN** the command runs with `--start 2026-09-09 --end 2026-10-09` and 21,804 bins have a `sub_district`
- **THEN** the calendar holds 21,804 x 31 rows, one per bin and date

#### Scenario: Single day
- **WHEN** start and end are the same date
- **THEN** each eligible bin has exactly one row, for that date

#### Scenario: Bin without sub-district
- **WHEN** a bin has a NULL `sub_district`
- **THEN** it has no rows in the calendar

#### Scenario: Bin without object group
- **WHEN** a bin has a NULL `object_group` and a non-NULL `sub_district`
- **THEN** it has a row for every date, with a NULL `object_group`

#### Scenario: Bin with no history
- **WHEN** an eligible bin has no service history events
- **THEN** it still has a row for every date

### Requirement: Calendar features of the row's date
Each row SHALL carry `date`, `day_of_week` (ISO, 1 for Monday to 7 for Sunday), `week_of_year` (ISO week number, 1 to 53), `month` (1 to 12) and `season` (meteorological, 1 for winter Dec–Feb, 2 for spring Mar–May, 3 for summer Jun–Aug, 4 for autumn Sep–Nov).

#### Scenario: Ordinary date
- **WHEN** a row's date is 2026-10-09 (a Friday)
- **THEN** `day_of_week` is 5, `week_of_year` is 41, `month` is 10 and `season` is 4

#### Scenario: December belongs to winter
- **WHEN** a row's date is 2026-12-01
- **THEN** `month` is 12 and `season` is 1

#### Scenario: ISO week across New Year
- **WHEN** a row's date is 2027-01-01 (a Friday)
- **THEN** `week_of_year` is 53 and `day_of_week` is 5

### Requirement: Bin attributes as stored at rebuild time
Each row SHALL carry `bin_id`, `site_id`, `waste_type`, `capacity_m3`, `sub_district` and `object_group` equal to the bin's stored values when the rebuild ran, the same on every date. These are current registry attributes applied to all dates, not historical observations. Later changes to `bins` SHALL NOT alter existing rows until the next rebuild.

#### Scenario: Attributes copied unchanged
- **WHEN** bin 3 has site 2, waste type `Mixed municipal waste`, capacity 1.1, sub-district `Panerių sen.` and object group `Komercinė paskirtis`
- **THEN** every calendar row of bin 3 has exactly those values

#### Scenario: Unknown capacity
- **WHEN** an eligible bin has a NULL `capacity_m3`
- **THEN** its rows have a NULL `capacity_m3`

### Requirement: Independence from service history
The calendar SHALL be derived only from the stored bins and the requested dates. It SHALL NOT read service history, and it SHALL NOT contain observed service outcomes, collection counts or fill levels.

#### Scenario: History changes do not matter
- **WHEN** service history is changed or emptied and the calendar is rebuilt with the same dates and bins
- **THEN** the calendar contents are identical to the previous rebuild

### Requirement: All-or-nothing replacement
A rebuild SHALL replace the entire previous calendar, including rows outside the new date range. Any failure SHALL leave the previous calendar exactly as it was.

#### Scenario: Narrower range replaces wider one
- **WHEN** the calendar holds 2026-09-01 to 2026-10-31 and the command runs with `--start 2026-09-09 --end 2026-10-09`
- **THEN** only dates from 2026-09-09 to 2026-10-09 remain

#### Scenario: Failure keeps previous contents
- **WHEN** a rebuild fails partway, for example because the connection is lost
- **THEN** the calendar keeps its previous rows and the command exits with 1

### Requirement: Rows of removed bins disappear
When a bin is deleted, its calendar rows SHALL be deleted with it. A collection CSV import that replaces `bins` SHALL leave the calendar empty until it is rebuilt.

#### Scenario: Synchronization cleanup removes a bin
- **WHEN** a VASA synchronization cleanup deletes a bin
- **THEN** that bin has no calendar rows and the rows of other bins remain

### Requirement: Clear output and exit codes
On success, the command SHALL report the date range, the number of days, the number of bins included, the number of bins excluded for a missing sub-district and the total rows, and exit with 0. It SHALL exit with 1 and a readable reason that does not disclose database credentials when an argument is invalid or the rebuild fails.

#### Scenario: Successful run summary
- **WHEN** the command runs with `--start 2026-09-09 --end 2026-10-09`
- **THEN** it reports 31 days, the included and excluded bin counts and the row count, and exits with 0

#### Scenario: Invalid date
- **WHEN** `--start` is `2026-13-01` or `--end` is not a date
- **THEN** the command changes nothing, names the bad value and exits with 1

#### Scenario: Reversed range
- **WHEN** `--start` is later than `--end`
- **THEN** the command changes nothing, says the range is reversed and exits with 1

### Requirement: Date range of at most five years
The command SHALL reject a range longer than 1,827 days, counting both the start and end dates, without connecting to the database. This is enough for any five calendar years including leap days, and it stops a mistyped year from creating hundreds of millions of rows.

#### Scenario: Five-year range accepted
- **WHEN** the command runs with `--start 2027-03-01 --end 2032-02-29` (1,827 days)
- **THEN** the calendar is rebuilt for that range and the command exits with 0

#### Scenario: Longer range rejected
- **WHEN** the command runs with `--start 2026-09-09 --end 2031-09-10` (1,828 days) or `--end 2062-10-09`
- **THEN** the command changes nothing, states the 1,827-day limit and the requested day count, and exits with 1
