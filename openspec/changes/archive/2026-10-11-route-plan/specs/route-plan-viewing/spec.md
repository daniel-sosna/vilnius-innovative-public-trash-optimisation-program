# Spec Delta

## Purpose

Lets administrators read a stored route plan and see each truck's trips on the map together with the savings against the baseline, so the result of route planning can be inspected and demonstrated.

## ADDED Requirements

### Requirement: Read a stored route plan
`GET /route-plans` with a required `date` (ISO `YYYY-MM-DD`) and `waste_carrier` SHALL return the stored plan of that carrier and date, or `404` when none is stored. Invalid or missing parameters SHALL return `422`.

#### Scenario: Stored plan
- **WHEN** a plan is stored for Ecoservice on 2026-09-16 and the endpoint is called with that date and carrier
- **THEN** the response has the stored plan

#### Scenario: No plan
- **WHEN** nothing is stored for the carrier and date
- **THEN** the endpoint returns `404`

#### Scenario: Invalid date
- **WHEN** the date is `2026-13-01` or omitted
- **THEN** the endpoint returns `422`

### Requirement: Content of a route plan response
A route plan response SHALL contain the parameters used, the summary of the optimised plan and of the baseline, the unserved stops with reasons, and for each truck its name, capacity, landfill and ordered trips. Each trip SHALL list its stops in order with site ID, address, coordinates and load, and the trip's load, estimated distance and duration.

#### Scenario: Trips in order
- **WHEN** a plan with a truck of two trips is read
- **THEN** the truck lists both trips in driving order, each with its ordered stops, load, distance and duration

#### Scenario: Summaries and unserved
- **WHEN** a plan with one unserved stop is read
- **THEN** the response has both summaries and the unserved stop with its reason

### Requirement: List available route plans
`GET /route-plans/available` SHALL return the stored (date, carrier) combinations, ordered by date descending then carrier, so the UI can offer only plans that exist. It SHALL return an empty list when none are stored.

#### Scenario: Listing
- **WHEN** plans are stored for two carriers on one date
- **THEN** the endpoint lists both combinations

#### Scenario: Nothing stored
- **WHEN** no plan is stored
- **THEN** the endpoint returns an empty list with `200`

### Requirement: Route plan page
The admin navigation SHALL contain `Maršrutai`, linked to `/admin/routes`. The page SHALL be in Lithuanian, offer a choice of a stored plan (date and carrier), and show a map with the selected plan. When no plan exists, the page SHALL say so and name the command that creates it, without an error state.

#### Scenario: Open the page
- **WHEN** an administrator opens `Maršrutai`
- **THEN** the page offers the stored plans and shows the most recent one on the map

#### Scenario: Nothing stored
- **WHEN** no plan is stored
- **THEN** the page shows a message that no route plan exists and names the command

### Requirement: Trucks, trips and stops on the map
The map SHALL show each truck's trips in one colour per truck, with the landfill, the stops numbered in visiting order and straight lines between consecutive points of a trip. Selecting a truck SHALL highlight its routes and list its trips with load, estimated distance and duration. Trucks without trips SHALL be listed as unused. The estimated, straight-line nature of the routes SHALL be stated on the page.

#### Scenario: One colour per truck
- **WHEN** a plan with several trucks is shown
- **THEN** each truck's trips have their own colour and every stop shows its position in its trip

#### Scenario: Select a truck
- **WHEN** an administrator selects a truck
- **THEN** its routes are highlighted and its trips are listed with load, distance and duration

#### Scenario: Idle truck
- **WHEN** a truck has no trips
- **THEN** it appears in the list as unused and has no route on the map

### Requirement: Savings and warnings on the page
The page SHALL show, for the optimised plan and the baseline, the distance, trips, trucks used and overtime, together with the distance saved in km and percent. It SHALL show the number of unserved stops with reasons and the number of trucks excluded, and SHALL state that loads come from predictions on synthetic data and that distances are estimates.

#### Scenario: Savings panel
- **WHEN** a plan is shown
- **THEN** the panel shows both plans' figures, the saving and the overtime of both

#### Scenario: Unserved stops
- **WHEN** the plan has unserved stops
- **THEN** the page lists them with the reason and their share of the carrier's stops

#### Scenario: Data caveat
- **WHEN** a plan is shown
- **THEN** the page states that the loads are predicted from synthetic history and the distances are straight-line estimates
