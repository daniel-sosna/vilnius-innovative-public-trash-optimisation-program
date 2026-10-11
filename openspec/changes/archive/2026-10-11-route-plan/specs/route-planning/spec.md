# Spec Delta

## Purpose

Turns a carrier's due stops for a date into a stored daily route plan for each of its trucks, and measures the driving it saves against a naive plan for the same stops, so routes can be shown and evaluated.

## ADDED Requirements

### Requirement: Inputs of one carrier and one date
The plan SHALL be computed for one waste carrier and one date, from that carrier's due stops in the collection plan of the date and from the carrier's trucks that are available, not deleted and have a landfill. A stop's load SHALL be its `overall_predicted_fill_m3`; `overall_volume_m3` SHALL NOT be used. Any truck SHALL be able to carry any waste type. Other carriers and unassigned stops SHALL NOT be planned.

#### Scenario: Only the carrier's stops and eligible trucks
- **WHEN** the plan is computed for Ecoservice on a date with stops of three carriers and trucks of two carriers
- **THEN** only Ecoservice's stops are planned and only Ecoservice's available, nondeleted trucks with a landfill are used

#### Scenario: Truck without landfill
- **WHEN** an available Ecoservice truck has no landfill
- **THEN** it is not used and the summary counts it as excluded

#### Scenario: No eligible truck
- **WHEN** the carrier has no eligible truck
- **THEN** the command exits with code 1, names the reason and changes nothing

#### Scenario: No stops
- **WHEN** the carrier has no due stop on the date
- **THEN** the command reports that there is nothing to plan, exits with code 1 and changes nothing

### Requirement: Trips from the truck's landfill
Each truck's day SHALL consist of zero or more trips. A trip SHALL start and end at the truck's own landfill and visit an ordered list of stops. The sum of the loads of a trip's stops SHALL NOT exceed the truck's `max_volume_m3`. A truck SHALL unload at its landfill between trips. Every stop SHALL be visited at most once, and a truck MAY be left without trips.

#### Scenario: Load per trip within capacity
- **WHEN** a plan is stored
- **THEN** for every trip the summed stop loads are at most the truck's maximum volume

#### Scenario: Several trips per truck
- **WHEN** a truck's stops together exceed its maximum volume
- **THEN** its stops are split into trips, each starting and ending at the truck's landfill

#### Scenario: Idle trucks
- **WHEN** one truck can serve all stops within its shift
- **THEN** the other trucks may have no trips and the plan is still valid

### Requirement: Every due stop is served
Every due stop of the carrier SHALL appear in exactly one trip, except a stop whose load alone exceeds the maximum volume of every eligible truck. Such a stop SHALL NOT be planned and SHALL be listed as unserved with that reason. A stop with load 0 SHALL be planned normally. Stops SHALL NOT be dropped for lack of trucks or time.

#### Scenario: All stops served
- **WHEN** every stop's load fits at least one eligible truck
- **THEN** every due stop appears in exactly one trip and the unserved count is 0

#### Scenario: Oversize stop
- **WHEN** a stop's load is 30 m3 and the largest eligible truck holds 20 m3
- **THEN** the stop is reported as unserved with the reason that it exceeds every truck's capacity, and the rest of the plan is stored

### Requirement: Shift time and soft overtime
The plan SHALL compute each truck's day duration from driving time, service time at each stop and unloading time at the landfill, using the stored time assumptions. Time beyond the shift length SHALL be overtime, which the plan SHALL allow but penalise at a cost per overtime minute that exceeds the cost of the extra kilometres needed to give the work to another truck, so the plan avoids overtime while any truck can take the work within its shift. Trucks left idle on a light day are acceptable.

#### Scenario: Overtime only when trucks are busy
- **WHEN** the fleet can serve all stops within the shift
- **THEN** the plan has no overtime

#### Scenario: Fleet too small
- **WHEN** the fleet cannot serve all stops within the shift
- **THEN** every stop is still served, the summary reports the overtime per truck and the total, and the plan's total overtime is no greater than the baseline's

### Requirement: Distances and time assumptions
Distances SHALL be straight-line distances between coordinates multiplied by a detour factor, not road distances, and SHALL be documented as an estimate. Driving time SHALL come from an average speed. Average speed, detour factor, service time per stop, unloading time, shift length, overtime penalty, solver effort limit and random seed SHALL have documented defaults, SHALL be overridable on the command, and SHALL be stored with each plan.

#### Scenario: Parameters stored
- **WHEN** a plan is computed with a different average speed
- **THEN** the stored plan holds the speed used, and its distances and times follow it

#### Scenario: Estimate is labelled
- **WHEN** a distance or duration is shown or printed
- **THEN** it is identified as an estimate based on straight-line distance

### Requirement: Baseline plan for comparison
Every computed plan SHALL be compared with a baseline for the same stops, trucks, loads, capacity, trip, shift and distance rules. The baseline SHALL be nearest-neighbour: a truck repeatedly drives to the nearest unserved stop that still fits, returns to its landfill to unload when no stop fits, and trucks take turns until all stops are served. The baseline SHALL be documented.

#### Scenario: Same stops in both plans
- **WHEN** a plan and its baseline are computed
- **THEN** both serve exactly the same set of stops

#### Scenario: Baseline respects the same limits
- **WHEN** the baseline is stored
- **THEN** none of its trips exceeds its truck's maximum volume and its overtime is measured with the same shift rule

### Requirement: Measured savings
The plan SHALL store, for the optimised plan and for the baseline, the total distance in km, number of trips, number of trucks used, total overtime in minutes and the number of stops served. It SHALL also store the distance saved in km and as a percentage of the baseline, and the number of unserved stops. The savings SHALL be stored and printed together with the overtime of both plans, so a saving is never shown without it.

#### Scenario: Savings summary
- **WHEN** a plan is computed
- **THEN** the summary shows km, trips, trucks used and overtime for both plans, the km saved with its percentage and the unserved stops

#### Scenario: Equal to the baseline
- **WHEN** the optimised plan is no shorter than the baseline
- **THEN** the saving is reported as 0 or negative and is not hidden

### Requirement: Stored plan survives collection-plan changes
A stored route plan SHALL keep, for each planned stop, its site, address, coordinates, load and the number of bins, and for each truck its name, maximum volume and landfill, copied at planning time. It SHALL NOT be changed or removed when the collection plan of the date is rebuilt or when a truck is changed, retired or deleted. Deleting a site SHALL NOT delete a stored route plan; the stop keeps its copied data.

#### Scenario: Collection plan rebuilt
- **WHEN** the collection plan of the date is rebuilt after the route plan was stored
- **THEN** the stored route plan is unchanged and still readable

#### Scenario: Truck retired
- **WHEN** a truck of a stored plan is retired or replaced
- **THEN** the route plan still shows the truck with its name, capacity and landfill as planned

#### Scenario: Site deleted
- **WHEN** a site that is in a stored route plan is deleted
- **THEN** the route plan still lists the stop with its copied address and coordinates

### Requirement: Rerun replaces one carrier and date
The command SHALL replace the stored plan of the given carrier and date in one transaction and leave other carriers and dates unchanged. A failure, including a failed solve, SHALL leave the previous plan unchanged. The command SHALL run only when invoked explicitly.

#### Scenario: Rerun replaces
- **WHEN** the plan of Ecoservice on 2026-09-16 is computed twice with different parameters
- **THEN** only the second plan is stored and other carriers and dates are unchanged

#### Scenario: Failure leaves previous plan
- **WHEN** the solve or the database write fails
- **THEN** the previous plan of the carrier and date is unchanged and the command exits with code 1

### Requirement: Command arguments, summary and exit codes
The command SHALL require a carrier and a date and SHALL reject an invalid date, an unknown option value or a date without a collection plan before changing anything. It SHALL print the carrier, date, trucks used and excluded, stops planned and unserved, the parameters, the savings summary and the solve time. It SHALL exit 0 on success and 1 on invalid arguments, missing input, database failure or a solve failure. Output SHALL NOT disclose database credentials.

#### Scenario: Successful run
- **WHEN** the command runs for a carrier and date with stops and eligible trucks
- **THEN** it stores the plan, prints the summary and exits 0

#### Scenario: Missing argument
- **WHEN** the carrier or the date is omitted
- **THEN** the command exits with code 1 and changes nothing

#### Scenario: Date without collection plan
- **WHEN** no collection plan exists for the date
- **THEN** the command reports that the collection plan must be built first, exits with code 1 and changes nothing

### Requirement: Repeatable result
With unchanged stops, trucks and parameters, including the random seed and effort limit, the plan SHALL be repeatable: running it again SHALL give the same stored plan on the same machine. The stored parameters SHALL be enough to rerun the computation.

#### Scenario: Same inputs and seed
- **WHEN** the plan is computed twice with the same inputs and parameters
- **THEN** both runs store the same trips and the same distances
