# bin-day-calendar Specification

## Purpose

Provides a stored grid of every eligible bin on every day of an operator-chosen date range, with calendar features and bin attributes, as the input contract for synthetic fill-level generation.

## Requirements

### Requirement: Rebuild only on explicit invocation
The bin-day calendar SHALL change only when an operator runs the rebuild command with a start date and an end date. The command SHALL work inside the backend container and natively, using the existing database configuration. Application startup, migrations and idle runtime SHALL NOT build or change it.

#### Scenario: Startup leaves the calendar alone
- **WHEN** the backend starts or migrations run
- **THEN** the bin-day calendar contents are unchanged

#### Scenario: Both dates are required
- **WHEN** the command is run without `--start` or without `--end`
- **THEN** it changes nothing, explains the missing argument and exits with 1

### Requirement: One row per eligible bin per day
After a rebuild for `--start S --end E`, the calendar SHALL contain exactly one row for each eligible bin and each date from S to E inclusive, and no other rows. A bin is eligible when its `sub_district` is not NULL and it has at least one stored planned collection date. Every eligible bin SHALL appear on every date, whatever its service history.

#### Scenario: Current history period
- **WHEN** the command runs with `--start 2026-09-09 --end 2026-10-09` and 21,695 bins have both a `sub_district` and planned dates
- **THEN** the calendar holds 21,695 x 31 rows, one per bin and date

#### Scenario: Single day
- **WHEN** start and end are the same date
- **THEN** each eligible bin has exactly one row, for that date

#### Scenario: Bin without sub-district
- **WHEN** a bin has a NULL `sub_district`
- **THEN** it has no rows in the calendar

#### Scenario: Bin without schedule
- **WHEN** a bin has a `sub_district` but no stored planned dates
- **THEN** it has no rows in the calendar and is counted as excluded for a missing schedule

#### Scenario: Bin without object group
- **WHEN** a bin has a NULL `object_group`, a non-NULL `sub_district` and planned dates
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
The calendar SHALL be derived only from the stored bins, their stored planned dates, their stored resident allocation, the requested dates, the Lithuanian public holiday calendar and the simulation parameters. It SHALL NOT read service history, and it SHALL NOT contain observed service outcomes or fill levels. Its collection status and collection counts are synthetic, simulated from the schedule, and are not observations.

#### Scenario: History changes do not matter
- **WHEN** service history is changed or emptied and the calendar is rebuilt with the same dates, bins, planned dates, resident allocation, seed and parameters
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
On success, the command SHALL report the date range, the number of days, the number of bins included, the numbers of bins excluded for a missing sub-district and for a missing schedule, the total rows, the seed and failure parameters used, and the number of rows per collection status. It SHALL then exit with 0. It SHALL exit with 1 and a readable reason that does not disclose database credentials when an argument is invalid or the rebuild fails.

#### Scenario: Successful run summary
- **WHEN** the command runs with `--start 2026-09-09 --end 2026-10-09`
- **THEN** it reports 31 days, the included bin count, both excluded bin counts, the row count, the seed, the four failure parameters and the count of each collection status, and exits with 0

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

### Requirement: Stored schedule repeats over the whole range
Each eligible bin's stored planned dates SHALL be treated as one repeating cycle. With one stored date the cycle is 28 days; otherwise it is the shortest of 1, 7, 14, 21 or 28 days whose repetition gives exactly the stored dates within the calendar months they cover, or 28 days if none does. A day is planned when its distance from a stored date is a multiple of the cycle length. This assumes the schedule does not change over time.

#### Scenario: Weekly schedule
- **WHEN** a bin's stored dates are 2026-10-07, 2026-10-14, 2026-10-21 and 2026-10-28
- **THEN** 2026-09-30 and 2026-11-04 are planned days and 2026-11-05 is not

#### Scenario: Several weekdays
- **WHEN** a bin's stored dates are every Monday, Wednesday and Friday of October 2026
- **THEN** every Monday, Wednesday and Friday of the range is a planned day, and no other day is

#### Scenario: Two-weekly schedule keeps its phase
- **WHEN** a bin's stored dates are 2026-10-06 and 2026-10-20
- **THEN** 2026-11-03 is a planned day and 2026-10-27 is not

#### Scenario: Daily schedule
- **WHEN** a bin has every day of October 2026 stored
- **THEN** every day of the range is a planned day

#### Scenario: Single date in the month
- **WHEN** a bin's only stored date is 2026-10-15
- **THEN** the planned days are every 28 days from it, including 2026-11-12 and 2026-09-17

#### Scenario: Irregular dates
- **WHEN** a bin's only stored dates are 2026-10-01 and 2026-10-08
- **THEN** the cycle is 28 days, and 2026-10-29 and 2026-11-05 are planned days

#### Scenario: Schedule changes after the rebuild
- **WHEN** `bin_schedule` is refreshed after a rebuild
- **THEN** existing calendar rows are unchanged until the next rebuild

### Requirement: Simulated collection attempts
On each planned day, a collection SHALL be attempted. A failed attempt SHALL be retried on the next day, and if that fails, once more on the day after. A planned day cancels any pending retry and starts a new first attempt. A bin SHALL have at most one attempt per day. Each attempt independently succeeds or fails at random with the probability for its kind: first attempt, first retry or second retry.

#### Scenario: Retry succeeds
- **WHEN** a weekly bin's attempt fails on its planned Monday and the retry on Tuesday succeeds
- **THEN** Wednesday has no attempt, and the next attempt is on the following Monday

#### Scenario: Both retries fail
- **WHEN** a weekly bin's first attempt on Monday, its retry on Tuesday and its retry on Wednesday all fail
- **THEN** Thursday to Sunday have no attempt, and the next attempt is a first attempt on the following Monday

#### Scenario: Planned day cancels retries
- **WHEN** a bin planned on Mondays and Tuesdays fails on Monday
- **THEN** Tuesday's attempt is a first attempt, not a retry

### Requirement: Collection status of the day
Each row SHALL carry `collection_status`, the outcome of that day's own attempt: `none` when there is no attempt, `collected` when a first attempt succeeds, `retry_collected` when a retry succeeds, `failed` when an attempt fails and a retry follows the next day, and `missed` when an attempt fails and no retry follows. `collected` and `retry_collected` are successful collections.

#### Scenario: Statuses of a missed occurrence
- **WHEN** a weekly bin fails its first attempt on Monday and both retries
- **THEN** Monday and Tuesday are `failed`, Wednesday is `missed`, and Thursday to Sunday are `none`

#### Scenario: Failure right before a planned day
- **WHEN** a daily bin's attempt fails
- **THEN** that day is `missed`, because the next day is a planned day and starts a new first attempt

#### Scenario: Retry success
- **WHEN** a first attempt fails and the next day's retry succeeds
- **THEN** the first day is `failed` and the second is `retry_collected`

### Requirement: Failure probabilities
The failure probability of an attempt SHALL be set by `--p-first` (default 0.028), `--p-retry1` (default 0.40) and `--p-retry2` (default 0.70). On a Lithuanian public holiday it SHALL be multiplied by `--holiday-factor` (default 2) and capped at 0.95. These defaults are assumptions, not values measured from observed history.

#### Scenario: Holiday attempt
- **WHEN** a first attempt falls on 2026-11-01 with default parameters
- **THEN** its failure probability is 0.056

#### Scenario: Cap on holidays
- **WHEN** `--p-retry2 0.70 --holiday-factor 2` and a second retry falls on a holiday
- **THEN** its failure probability is 0.95

#### Scenario: Never failing
- **WHEN** `--p-first 0` is given
- **THEN** every planned day has status `collected`

#### Scenario: Invalid probability
- **WHEN** any probability is below 0 or above 1, or `--holiday-factor` is negative
- **THEN** the command changes nothing, names the bad value and exits with 1 without connecting to the database

### Requirement: Lithuanian public holidays
Holidays SHALL be the public holidays (non-working days) of Lithuania for each date, including movable ones: Easter Sunday and Monday, Mother's Day (first Sunday of May) and Father's Day (first Sunday of June).

#### Scenario: Fixed holiday
- **WHEN** a date is 2026-12-24
- **THEN** it is a holiday

#### Scenario: Movable holidays
- **WHEN** the range includes Easter 2027
- **THEN** 2027-03-28 and 2027-03-29 are holidays

### Requirement: Holidays since last collection
Each row SHALL carry `holidays_since_last_collection`, the number of holidays from the day after the bin's latest successful collection before the row's date through the day before the row's date. When the bin has no successful collection since the simulation start, counting SHALL start at the simulation start.

#### Scenario: Collected yesterday
- **WHEN** the bin's latest successful collection was the day before the row's date
- **THEN** the value is 0

#### Scenario: Holidays while filling
- **WHEN** a bin was last collected on 2026-10-30 and the row's date is 2026-11-04
- **THEN** the value is 2, for 2026-11-01 and 2026-11-02

#### Scenario: Today's collection is not counted
- **WHEN** the row's own status is `collected`
- **THEN** the value is still counted from the previous successful collection

### Requirement: Collections in the last 28 days
Each row SHALL carry `collections_last_28d`, the number of days with a successful collection of that bin from the row's date − 28 through the row's date − 1. The row's own day SHALL NOT count.

#### Scenario: Weekly bin without failures
- **WHEN** a weekly bin was collected on each of its 4 planned days in the 28 days before the row's date
- **THEN** the value is 4

#### Scenario: Retry counts once
- **WHEN** an occurrence failed and was collected on a retry inside the window
- **THEN** it adds 1

### Requirement: Missed collections in the last 28 days
Each row SHALL carry `missed_collections_28d`, the number of days with status `missed` for that bin from the row's date − 28 through the row's date − 1. A planned collection counts as missed only when all its attempts failed. It counts on the day the miss became final, not on the planned day.

#### Scenario: Collected on a retry
- **WHEN** an occurrence failed on its planned day and succeeded on a retry
- **THEN** it does not add to the value

#### Scenario: Miss becomes final after retries
- **WHEN** an occurrence planned on 2026-10-05 failed on 2026-10-05, 2026-10-06 and 2026-10-07
- **THEN** rows dated 2026-10-08 through 2026-11-04 count it, and the row dated 2026-10-07 does not

### Requirement: Warm-up before the range
The simulation SHALL start 35 days before `--start`, so that the first written rows have complete 28-day features. Rows SHALL be written only for dates from `--start` to `--end`. The 1,827-day limit SHALL count only the written dates.

#### Scenario: First row has history
- **WHEN** a weekly bin without failures is rebuilt with `--start 2026-09-09`
- **THEN** its row for 2026-09-09 has `collections_last_28d` equal to 4

### Requirement: Reproducible simulation
The command SHALL accept `--seed`, an integer with default 42. Two rebuilds with the same dates, bins, planned dates, seed and parameters SHALL produce identical calendars. A different seed SHALL generally produce different outcomes.

#### Scenario: Same seed
- **WHEN** the command runs twice with `--start 2026-09-09 --end 2026-10-09 --seed 7`
- **THEN** both calendars are identical

#### Scenario: Default seed
- **WHEN** the command runs twice without `--seed`
- **THEN** both calendars are identical, and the summary reports seed 42

### Requirement: Population attributes of the bin
Each row SHALL carry `population_cell_id` and `resident_factor`, equal to the bin's stored resident allocation when the rebuild ran, the same on every date. `population_cell_id` SHALL be NULL when the bin lies in no population polygon. `resident_factor` is an estimate derived from population data, not an observation, and later reallocations SHALL NOT alter existing rows until the next rebuild.

#### Scenario: Values copied unchanged
- **WHEN** bin 3 is allocated to population polygon 5123 with resident factor 37.4
- **THEN** every calendar row of bin 3 has `population_cell_id` 5123 and `resident_factor` 37.4

#### Scenario: Non-residential bin
- **WHEN** an eligible bin's resident factor is 0
- **THEN** its rows have `resident_factor` 0

#### Scenario: Reallocation after the rebuild
- **WHEN** the resident allocation is rebuilt with another suppressed density after the calendar was rebuilt
- **THEN** existing calendar rows are unchanged until the next calendar rebuild

### Requirement: Rebuild requires a current resident allocation
The rebuild SHALL refuse to run when any eligible bin has no stored resident allocation. It SHALL change nothing, report how many eligible bins lack one, name the command that rebuilds the allocation and exit with 1.

#### Scenario: Allocation never built
- **WHEN** bins were imported and the bin population command has not run since
- **THEN** the calendar rebuild changes nothing, says that 21,840 eligible bins have no resident allocation, names `python -m app.interfaces.bin_population` and exits with 1

#### Scenario: Bin added after allocation
- **WHEN** a synchronization adds an eligible bin after the last allocation rebuild
- **THEN** the calendar rebuild changes nothing, reports 1 bin without allocation and exits with 1
