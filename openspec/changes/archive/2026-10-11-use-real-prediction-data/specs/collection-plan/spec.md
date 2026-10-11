## REMOVED Requirements

### Requirement: Predicted fill level per bin
**Reason**: The mock prediction is replaced by the trained model.
**Migration**: See "Fill level from the trained model" and "Historical data and model must be present".

## ADDED Requirements

### Requirement: Fill level from the trained model
The plan SHALL be built from the trained next-day fill-level model (see `daily-fill-prediction`), which gives a bin one fill level for the plan date, an integer from 0 (empty) to 4 (full). A bin for which the model gives no level SHALL be left out of the plan. Levels for bins that are not stored SHALL be ignored. The levels are predicted from synthetic assessment history, not observed, and SHALL be documented as such.

#### Scenario: Levels come from the model
- **WHEN** the plan is built for a valid date with stored bins that the model covers
- **THEN** every such bin is evaluated with the level the model predicts for the plan date, between 0 and 4

#### Scenario: Bin without a prediction
- **WHEN** a stored bin has no predicted level
- **THEN** the bin is not evaluated, is never due, and does not appear in any stop, and the build still succeeds

#### Scenario: Prediction for an unknown bin
- **WHEN** the model gives a level for a bin that is not stored
- **THEN** that level is ignored and does not affect the plan

#### Scenario: Reproducible per date
- **WHEN** the plan is built twice for the same date with unchanged bins and unchanged input files
- **THEN** both runs assign the same fill level to every bin and store identical stops

### Requirement: Historical data and model must be present
The plan SHALL be built only when the historical daily data, the bin registry export, the population export and the delivered model are present in the data directory. If any is missing, the command SHALL exit with code 1, name what is missing (for example "Historical data is not present in the system"), and leave every stored plan unchanged.

#### Scenario: Historical data missing
- **WHEN** the plan is built and the historical daily data file is absent from the data directory
- **THEN** the command reports that historical data is not present in the system, exits with code 1 and changes nothing

#### Scenario: Model missing
- **WHEN** the delivered model is absent from the data directory
- **THEN** the command reports that the model is not present, exits with code 1 and changes nothing

## MODIFIED Requirements

### Requirement: Threshold selects due bins
A bin SHALL be due when its predicted fill level is strictly greater than the threshold. The threshold SHALL be an integer from 0 to 4, defaulting to 2. Values outside that range SHALL be rejected before anything changes.

#### Scenario: Default threshold
- **WHEN** the plan is built without a threshold
- **THEN** bins predicted at 3 or 4 are due and bins at 0, 1 or 2 are not

#### Scenario: Threshold 4 selects nothing
- **WHEN** the plan is built with threshold 4
- **THEN** the date's plan is empty and the summary reports zero due bins

#### Scenario: Invalid threshold
- **WHEN** the threshold is 5 or -1
- **THEN** the command exits with code 1 and the stored plan is unchanged

### Requirement: Rebuild replaces one date atomically
The rebuild command SHALL require a date `T` (ISO `YYYY-MM-DD`) meaning "today", and an optional threshold. `T` SHALL be from 2026-09-01 through 2026-09-30; the levels SHALL be predicted from history through `T` inclusive for the next day `T+1`, and the plan SHALL be stored under `T+1`. The command SHALL replace all stops of `T+1` in one transaction, leaving other dates unchanged. A failure SHALL leave the previous plan of `T+1` unchanged. The command SHALL run only when invoked explicitly.

#### Scenario: Plan is stored for the next day
- **WHEN** the plan is built with date 2026-09-15
- **THEN** the stops are stored under 2026-09-16 and reading the plan for 2026-09-15 is unaffected

#### Scenario: Last day of the window
- **WHEN** the plan is built with date 2026-09-30
- **THEN** the stops are stored under 2026-10-01

#### Scenario: Rerun replaces the date
- **WHEN** the plan for 2026-09-16 is rebuilt with threshold 3 after a build with threshold 2
- **THEN** the stored plan for 2026-09-16 contains only bins predicted at 4, and the plan for 2026-09-15 is unchanged

#### Scenario: Date outside September
- **WHEN** the date is 2026-10-11 or 2026-08-31
- **THEN** the command reports that only September 2026 is available for simulation, exits with code 1 and changes nothing

#### Scenario: Date omitted
- **WHEN** the command is run without a date
- **THEN** it exits with code 1 and changes nothing

#### Scenario: Invalid date
- **WHEN** the date is `2026-13-01`
- **THEN** the command exits with code 1 and nothing changes

### Requirement: Summary and exit codes
The command SHALL print the given date, the plan date, threshold, prediction source (the trained model, with levels from synthetic history), number of bins evaluated, due bins, stops per carrier, unassigned stops and bins without capacity among the bins of the stops. It SHALL exit 0 on success, and 1 on invalid arguments, missing input data or model, database failure or when no bins are stored. Output SHALL NOT disclose database credentials.

#### Scenario: Successful run
- **WHEN** the plan is built with stored bins and all inputs present
- **THEN** the command prints the counts, names the model as the source and exits 0

#### Scenario: No bins stored
- **WHEN** the bins table is empty
- **THEN** the command reports that no bins are stored, changes nothing and exits 1
