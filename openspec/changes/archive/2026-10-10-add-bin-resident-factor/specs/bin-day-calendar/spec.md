# Spec Delta

## MODIFIED Requirements

### Requirement: Independence from service history
The calendar SHALL be derived only from the stored bins, their stored planned dates, their stored resident allocation, the requested dates, the Lithuanian public holiday calendar and the simulation parameters. It SHALL NOT read service history, and it SHALL NOT contain observed service outcomes or fill levels. Its collection status and collection counts are synthetic, simulated from the schedule, and are not observations.

#### Scenario: History changes do not matter
- **WHEN** service history is changed or emptied and the calendar is rebuilt with the same dates, bins, planned dates, resident allocation, seed and parameters
- **THEN** the calendar contents are identical to the previous rebuild

## ADDED Requirements

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
