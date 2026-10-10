# collection-schedules Specification

## Purpose

Stores VASA's planned collection dates for each stored bin as a current-month snapshot, refreshed by an explicitly invoked command, so prioritisation and routing can tell which bins are due.

## Requirements

### Requirement: Fetch schedules only on explicit invocation
Schedule fetching SHALL run only when an operator invokes the schedule command, inside the backend container or natively, using the existing database and VASA timeout configuration. Application startup, migrations, CSV import, bin synchronization and idle runtime SHALL NOT fetch schedules.

#### Scenario: Startup does not fetch schedules
- **WHEN** the backend starts with stored bins
- **THEN** no schedule request is made and `bin_schedule` is unchanged

#### Scenario: Native invocation
- **WHEN** `python -m app.interfaces.bin_schedule_sync` is run from `backend/` with settings in the root `.env`
- **THEN** it fetches schedules for the stored bins without other variables being exported

### Requirement: Planned dates are stored per bin
For each stored bin, the command SHALL request VASA's schedule by the bin's external ID and store one row per distinct planned date, linked to the bin. Planned dates SHALL be stored as calendar dates without a time of day. They are VASA's plan, distinct from observed service history.

#### Scenario: Store a weekly plan
- **WHEN** VASA returns `["2026-10-07", "2026-10-14", "2026-10-21", "2026-10-28"]` for bin 135353
- **THEN** that bin has exactly those four planned dates

#### Scenario: Duplicate dates in a response
- **WHEN** a response lists the same date twice
- **THEN** the bin has that date once

### Requirement: Each successful response replaces the bin's schedule
A valid response SHALL replace all stored planned dates of that bin, including dates from earlier months, so the table holds only the latest fetched plan. Each bin's replacement SHALL commit atomically and independently of other bins.

#### Scenario: Refresh in a new month
- **WHEN** a bin has October dates stored and a November run returns November dates
- **THEN** the bin has only the November dates

#### Scenario: Plan changed within the month
- **WHEN** a re-run returns a date set that differs from the stored one
- **THEN** the stored dates equal the new response exactly

#### Scenario: Empty response
- **WHEN** VASA returns `{"schedule": []}` for a bin that has stored dates
- **THEN** the bin has no planned dates and is counted as empty in the summary

### Requirement: Failed bins keep their previous schedule
A request that fails after retries, or a response that is not a JSON object with a `schedule` list of ISO `YYYY-MM-DD` dates, SHALL leave that bin's stored dates unchanged. The failure SHALL be reported with the bin's external ID and SHALL NOT stop the other bins.

#### Scenario: Unavailable source for one bin
- **WHEN** one bin's request keeps failing while others succeed
- **THEN** that bin keeps its previous dates, the others are refreshed, and the failure is reported

#### Scenario: Malformed date
- **WHEN** a response contains `"07/10/2026"` or a non-string entry
- **THEN** none of that response's dates are stored and the bin keeps its previous dates

### Requirement: Interrupted runs are recovered by re-running
The command SHALL NOT keep resume state. A run that is interrupted SHALL leave every bin either with its previous dates or with its fully replaced dates. Running the command again SHALL refresh all bins.

#### Scenario: Interrupted run
- **WHEN** the process stops after some bins were committed
- **THEN** the committed bins have their new dates, the others keep their previous dates, and the next run refreshes every bin

### Requirement: Schedules follow bin removal
When a bin is deleted, its planned dates SHALL be deleted with it. A bin removed while the command is running SHALL be reported as a failure for that bin and SHALL NOT stop the run.

#### Scenario: Bin removed by synchronization cleanup
- **WHEN** `bin_sync` cleanup deletes a bin that has planned dates
- **THEN** its planned dates no longer exist

### Requirement: Bounded and limited runs
The command SHALL accept `--workers` (default 4, positive) to bound concurrent requests, and `--max-bins` (default 0 meaning all bins, non-negative) to process only the first N bins by ID. Invalid values SHALL be rejected before any request.

#### Scenario: Trial run
- **WHEN** the command is run with `--max-bins 20`
- **THEN** only the 20 lowest-ID bins are refreshed, the others are unchanged, and the run is reported as limited

#### Scenario: Invalid worker count
- **WHEN** the command is run with `--workers 0`
- **THEN** it exits with 1 before any request or write

### Requirement: Clear summary and exit codes
The command SHALL report how many bins were processed, refreshed with dates, refreshed empty and failed, plus the total number of planned dates stored. Exit codes SHALL match `bin_sync`: 0 when all bins were processed without failure, 1 when any bin failed, arguments or configuration are invalid, or no bins are stored, and 2 when a nonzero `--max-bins` run had no failures. Failure takes precedence over the limit. Reasons SHALL NOT disclose database credentials.

#### Scenario: Successful run
- **WHEN** the command runs without `--max-bins` and every bin returns a valid response
- **THEN** the summary shows the counts and the command exits with 0

#### Scenario: Limited run without failures
- **WHEN** the command is run with `--max-bins 20` and every requested bin succeeds
- **THEN** the summary says the run was limited to 20 bins and the command exits with 2

#### Scenario: Limited run with a failure
- **WHEN** the command is run with `--max-bins 20` and one bin fails
- **THEN** the command exits with 1

#### Scenario: No bins stored
- **WHEN** `bins` is empty
- **THEN** the command says that collection data must be imported first and exits with 1 without making requests

#### Scenario: Partial failure
- **WHEN** some bins fail
- **THEN** the summary lists the failed external IDs (or a count with the first IDs when many fail) and the command exits with 1
