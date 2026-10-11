# Spec Delta

## Purpose

Lets a truck driver follow a stored route plan on a phone as a navigation experience and record the observed fill level of every bin before emptying it. Route geometry and the truck position are simulated; routes, bins and observations are real stored data.

## ADDED Requirements

### Requirement: Driver entry and layout
The Driver screen SHALL be available at `/driver/:truck_id` and a truck picker at `/driver`; the role page's `Vairuotojas` option SHALL lead to the picker. Both SHALL use a mobile-first layout without the admin navbar, giving the map most of the viewport.

#### Scenario: Role page leads to the driver
- **WHEN** the user selects `Vairuotojas` on the role page
- **THEN** the truck picker opens and no admin navigation is shown

#### Scenario: Unknown truck
- **WHEN** `/driver/:truck_id` names a truck that does not exist or is deleted
- **THEN** the screen shows a clear not-found message and does not start a route

### Requirement: Driver route source
`POST /driver/route` with a `truck_id` SHALL build the route from the stored route plan of the truck's carrier for the fixed driver plan date: the truck's first trip gives the ordered stops, and the collection plan of that date gives every bin of the carrier at each stop. It SHALL read stored data only and SHALL NOT run prediction, route planning or read data files. Each bin SHALL carry its database `id`, `inventory_number` and `waste_type`.

#### Scenario: Route from stored plans
- **WHEN** the truck has a first trip of three stops stored in the collection plan
- **THEN** the response lists three stops in trip order, each with all the carrier's bins there and their inventory number and waste type, and the road path

#### Scenario: Not-due bins are included
- **WHEN** a stop has three bins of the carrier and one is due
- **THEN** all three bins are listed for the stop

#### Scenario: Landfill is not a stop
- **WHEN** the trip starts and ends at the landfill
- **THEN** the landfill is not returned as a stop

#### Scenario: Bin missing from the database
- **WHEN** a bin of the collection plan no longer exists
- **THEN** the endpoint fails with an error naming no internal details, and no route is returned

### Requirement: No stored plan states
The system SHALL distinguish a missing plan from an empty one. If the truck's carrier has no stored route plan for the date, or the truck has no trip in it, the screen SHALL show `Šiai dienai paruošto maršruto duomenų nėra.`. If none of the trip's stops is in the collection plan, it SHALL show `Šiandien suplanuotų konteinerių nėra.`. In both cases navigation SHALL NOT be requested.

#### Scenario: No plan
- **WHEN** nothing is stored for the carrier and date
- **THEN** the screen shows the missing-data message and no navigation starts

#### Scenario: Trip without collection stops
- **WHEN** none of the trip's stops is in the collection plan
- **THEN** the screen shows the empty message and no navigation starts

### Requirement: Navigation service contract
Route geometry SHALL be obtained through a navigation service that accepts the ordered stops and returns one ordered road path and, for each stop, its position on that path. The mock implementation SHALL return a fixed real-road path and place the stops in order, spaced evenly along it. Replacing the implementation SHALL NOT change the Driver screen or the `POST /driver/route` response.

#### Scenario: Stops lie on the path
- **WHEN** a route of N stops is built by the mock
- **THEN** each stop's position is a vertex of the path, the positions strictly increase, and the last stop is at the end of the path

#### Scenario: Invalid navigation result
- **WHEN** the service returns fewer than two path points, a non-finite coordinate, or non-increasing stop positions
- **THEN** the endpoint fails and the screen shows the route error with a retry action

### Requirement: Starting the route
The idle screen SHALL offer `Pradėti maršrutą`. While the route is being prepared the screen SHALL show `Ruošiamas maršrutas...`, and on success it SHALL enter navigation mode. It SHALL NOT mention files, parsing or the mock.

#### Scenario: Successful start
- **WHEN** the driver presses `Pradėti maršrutą` and a route is returned
- **THEN** the screen shows preparation text and then the navigation map with the truck at the start

#### Scenario: Preparation fails
- **WHEN** the route request fails
- **THEN** the screen shows an error with a retry action and no navigation starts

### Requirement: Road-following truck movement
In navigation mode the truck SHALL move through the ordered path coordinates and SHALL NOT move in straight lines between stops. The route ahead SHALL be drawn along the path, the completed part SHALL look different from the remaining part, and the truck marker SHALL face the direction of travel.

#### Scenario: Follows geometry
- **WHEN** the path bends between two stops
- **THEN** the truck passes through every path point between them in order

#### Scenario: Heading
- **WHEN** the truck moves along a segment
- **THEN** the marker is rotated to the segment's bearing

### Requirement: Follow camera
During navigation the map SHALL keep the truck in view, placed in the lower-middle part of the screen with the route ahead visible, and SHALL rotate with the driving direction without abrupt jumps. If the driver pans the map, following SHALL stop until the driver presses a recenter control that returns the camera to the truck.

#### Scenario: Automatic follow
- **WHEN** the truck advances
- **THEN** the camera center follows it without manual panning

#### Scenario: Manual pan and recenter
- **WHEN** the driver pans the map and then presses the recenter control
- **THEN** following stops after the pan and resumes after the control is pressed

### Requirement: Next stop and progress
During navigation the screen SHALL show the next stop as `Kitas konteineris` with its address and the `Inventorinis Nr.` and `Atliekų tipas` of its bins, and compact progress as serviced of total bins, for example `3 / 12 konteinerių`. On the map the next stop, future stops and serviced stops SHALL be visually distinct. It SHALL NOT show distances that are not derived from the data.

#### Scenario: Next bin shown
- **WHEN** the truck is driving toward a stop with several bins
- **THEN** the panel shows that stop and its bins, and progress counts serviced bins

#### Scenario: Stop states
- **WHEN** one stop is serviced, one is next and one is later
- **THEN** the map shows all three in distinguishable styles

### Requirement: Arrival pauses navigation
When the truck reaches the path position of the next stop, the truck SHALL stop and a bin-by-bin fill-level flow SHALL become the primary interface, covering every bin of that stop. The truck SHALL NOT move on until all of them are saved.

#### Scenario: Arrival
- **WHEN** the truck reaches a stop
- **THEN** movement stops and the first bin's fill-level view appears

#### Scenario: Stop with several bins
- **WHEN** a stop has three bins
- **THEN** the driver is taken through all three, one view each, before the truck moves on

### Requirement: Fill-level input
Each bin SHALL have its own view showing its inventory number and waste type, its position in the stop (for example `2 / 3`) and exactly five large touch options: 0 `Tuščias`, 1 `Mažiau nei pusė`, 2 `Daugiau nei pusė`, 3 `Pilnas`, 4 `Perpildytas`. Choosing an option SHALL record it and move to the next bin without a confirm button. A back control SHALL return to the previous bin with its choice shown and changeable. The view SHALL NOT use number fields or dropdowns and SHALL NOT be dismissible.

#### Scenario: Choose advances
- **WHEN** the driver taps `Pilnas` on the first of three bins
- **THEN** that choice is recorded and the second bin's view appears

#### Scenario: Back keeps the choice
- **WHEN** the driver is on the second bin and presses back
- **THEN** the first bin's view shows `Pilnas` highlighted, and choosing another option replaces it and moves forward

#### Scenario: No back on the first bin
- **WHEN** the first bin of the stop is shown
- **THEN** no back control that leaves the stop is offered

### Requirement: All-done view
When every bin of the stop has a level, the screen SHALL show an `Visi konteineriai pažymėti` view listing each bin with its chosen label, a back control to the last bin, and `Patvirtinti`. Nothing SHALL be stored before `Patvirtinti`.

#### Scenario: All reported
- **WHEN** the driver chooses a level for the last bin
- **THEN** the all-done view lists every bin with its level and nothing has been stored yet

#### Scenario: Back from all-done
- **WHEN** the driver presses back in the all-done view
- **THEN** the last bin's view appears with its choice shown

### Requirement: Recording a service
`POST /driver/service`, sent when the driver confirms the all-done view, with a non-empty list of `{bin_id, fill_level}` SHALL store one `bin_hist` row per bin with `was_serviced` true and the given level, in one transaction, with a timestamp assigned by the server from the Europe/Vilnius local clock. The client SHALL NOT supply it. If any item is invalid or any bin is unknown, nothing SHALL be written.

#### Scenario: Saved together
- **WHEN** a stop's three bins are posted with levels 0, 2 and 4
- **THEN** three serviced rows with those levels and a server timestamp exist

#### Scenario: Invalid level
- **WHEN** one item has fill level 5 or -1
- **THEN** the endpoint returns `422` and no row is stored

#### Scenario: Unknown bin
- **WHEN** one bin does not exist
- **THEN** the endpoint returns `404` and no row is stored, including for the other bins

#### Scenario: Duplicate bin in one request
- **WHEN** the same bin appears twice
- **THEN** the endpoint returns `422` and nothing is stored

#### Scenario: Same instant twice
- **WHEN** a row for a bin with the same timestamp and status already exists
- **THEN** the endpoint fails without storing any row of the request and the screen offers a retry

### Requirement: Save failure keeps the stop
If saving fails the all-done view SHALL stay open with every choice kept, the truck SHALL stay paused, the error toast `Nepavyko išsaugoti duomenų. Bandykite dar kartą.` SHALL show, and retry SHALL be possible. No bin SHALL be marked serviced and progress SHALL NOT change.

#### Scenario: Failure then retry
- **WHEN** saving fails and the driver confirms again successfully
- **THEN** the stop's bins are marked serviced only after the successful save

#### Scenario: Edit after failure
- **WHEN** saving fails and the driver goes back and changes one bin
- **THEN** the retry sends the changed level and the other choices unchanged

### Requirement: Resuming after a service
After the stop is saved, the all-done view SHALL close and the truck SHALL continue along the path toward the next stop, with the stop shown as serviced and progress updated by the stop's bin count.

#### Scenario: Continue
- **WHEN** a stop with three bins is saved
- **THEN** the truck moves again toward the next stop and progress increases by three

### Requirement: Route completion
When every bin of the route is serviced, the truck SHALL stop and the screen SHALL show `Maršrutas baigtas` and the number of serviced bins. The route SHALL NOT restart automatically.

#### Scenario: Completed
- **WHEN** the last bin is saved
- **THEN** the completion message and count are shown and the truck does not move

### Requirement: Explicit workflow state
The screen SHALL be in exactly one state at a time: idle, preparing route, navigating, at bin, saving service, completed or error. An action SHALL be accepted only in the state that allows it.

#### Scenario: Repeated confirmation
- **WHEN** the driver presses `Patvirtinti` twice while the save is running
- **THEN** only one request is sent and each bin is stored once

### Requirement: Mock and assumption disclosure
The documentation SHALL state that the path, the stop positions on the map and the truck position are simulated, that the plan date is a fixed value, and which stored data a Driver run needs.

#### Scenario: Documented
- **WHEN** a developer reads the driver documentation
- **THEN** it lists the mock parts, the fixed date and the prerequisite plans
