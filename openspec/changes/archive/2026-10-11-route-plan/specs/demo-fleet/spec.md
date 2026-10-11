# Spec Delta

## Purpose

Creates a reproducible demo fleet of trucks per carrier, sized from the stored collection plan of a date, because no real fleet data exists and route planning needs trucks to be demonstrable.

## ADDED Requirements

### Requirement: Fleet sized from the stored collection plan
The seed command SHALL require a date and create, for each carrier that has due stops on that date in the stored collection plan, enough trucks to serve the carrier's total predicted load within the shift with about 20% slack. The estimate SHALL use the stored load, an assumed truck capacity mix, the shift length and an assumed trip duration, and SHALL be documented as an estimate, not a guarantee. The trucks SHALL be invented demo data, not real fleet data, and SHALL be documented as such.

#### Scenario: Sized from load
- **WHEN** the command runs for a date whose collection plan holds stops of two carriers
- **THEN** each of those carriers gets a number of trucks derived from its load, and carriers without stops get none

#### Scenario: Estimate documented
- **WHEN** the command prints its result
- **THEN** it states the load, the assumed capacities and the number of trucks created per carrier

### Requirement: Capacity mix and landfills
Created trucks SHALL have capacities drawn from a small set of assumed sizes, SHALL be available and not deleted, and SHALL be spread over the stored landfills. Trucks SHALL have unique, recognisable names carrying a demo prefix. The mix, the landfill spread and the random seed SHALL be parameters with documented defaults.

#### Scenario: Valid trucks
- **WHEN** trucks are created
- **THEN** each has a positive finite maximum volume from the mix, an existing landfill, `available` true and a name starting with the demo prefix

#### Scenario: No landfills
- **WHEN** no landfill is stored
- **THEN** the command exits with code 1, names the reason and changes nothing

### Requirement: Marked, reproducible, replaceable
Trucks created by the command SHALL be identifiable by their prefix. A rerun SHALL replace only the trucks it created earlier and SHALL NOT change, retire or delete any other truck. With the same stored plan and parameters, the seed SHALL create the same trucks.

#### Scenario: Hand-entered trucks untouched
- **WHEN** the command runs and the fleet also holds trucks entered through the truck screen
- **THEN** the hand-entered trucks are unchanged

#### Scenario: Rerun
- **WHEN** the command runs twice with the same date and parameters
- **THEN** the fleet holds the same demo trucks once, not duplicated

#### Scenario: Plan changed between runs
- **WHEN** the collection plan is rebuilt and the command runs again
- **THEN** the demo fleet is replaced to match the new load

### Requirement: Required input and exit codes
The command SHALL exit 1, name the missing input and change nothing when the date is invalid or omitted, when the collection plan of the date holds no stops, or on a database failure. It SHALL exit 0 on success. Output SHALL NOT disclose database credentials.

#### Scenario: Date without collection plan
- **WHEN** the date has no stored collection plan
- **THEN** the command reports that the collection plan must be built first, exits with code 1 and changes nothing

#### Scenario: Success
- **WHEN** the command runs with a valid date and a stored plan
- **THEN** it prints the trucks created per carrier and exits 0
