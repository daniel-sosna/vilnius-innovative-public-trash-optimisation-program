# Spec Delta

## Purpose

Lets a truck driver follow the road route calculated for the selected day on a phone as a navigation experience and record the observed fill level of every bin before emptying it. The route and its road geometry are real planning results; the truck position is simulated.

## ADDED Requirements

### Requirement: Driver entry and layout
The Driver screen SHALL be available at `/driver/:truck_id` and a truck picker at `/driver`; the role page's `Vairuotojas` option SHALL lead to the picker. Both SHALL use a mobile-first layout without the admin navbar, giving the map most of the viewport. The picker SHALL list only trucks that have a calculated route for the selected day, with their stop counts.

#### Scenario: Role page leads to the driver
- **WHEN** the user selects `Vairuotojas` on the role page
- **THEN** the truck picker opens and no admin navigation is shown

#### Scenario: Picker lists routed trucks
- **WHEN** a route calculation for the selected day assigned routes to trucks 1 and 4
- **THEN** the picker lists exactly those two trucks

#### Scenario: Unknown truck
- **WHEN** `/driver/:truck_id` names a truck that does not exist or is deleted
- **THEN** the screen shows a clear not-found message and does not start a route

### Requirement: Selected project date
The Driver SHALL use the application-wide project date (see `project-date`) and follow the route of its forecast day, the day after it. It SHALL NOT keep its own date. The picker and idle screen SHALL show the forecast day. When the project date changes, the Driver SHALL start over from idle and SHALL NOT continue a route of another day.

#### Scenario: Forecast day shown
- **WHEN** the project date is 2026-09-14
- **THEN** the picker and idle screen show 2026-09-15 and the route of 2026-09-15 is requested

#### Scenario: Date changed
- **WHEN** the project date changes while a route is shown
- **THEN** the Driver returns to idle for the new day

### Requirement: Driver route source
`POST /driver/route` with `truck_id` and `project_date` SHALL return the truck's route from the newest route calculation of the forecast day run on the route planning screen (see `demo-planning`): its road path and its service stops in driving order. It SHALL NOT run prediction or route calculation. Each stop SHALL list every bin of the truck's carrier at the site, with database `id`, `inventory_number` and `waste_type`.

#### Scenario: Route from the calculation
- **WHEN** the newest calculation of the forecast day gave the truck three service stops
- **THEN** the response lists those three stops in driving order with their bins and the road path

#### Scenario: Not-due bins are included
- **WHEN** a stop was planned for one due bin and the carrier has three bins at that site
- **THEN** all three bins are listed for the stop

#### Scenario: Landfill is not a stop
- **WHEN** the route returns to the landfill between and after trips
- **THEN** the returns are part of the path but are not stops

#### Scenario: Bin missing from the database
- **WHEN** a planned bin no longer exists
- **THEN** the endpoint fails with an error naming no internal details, and no route is returned

### Requirement: No route states
If no route calculation of the forecast day is available, or it gave the truck no route, the screen SHALL show `Šiai dienai paruošto maršruto duomenų nėra.`. If the route has no service stops, it SHALL show `Šiandien suplanuotų konteinerių nėra.`. In both cases navigation SHALL NOT start.

#### Scenario: No calculation
- **WHEN** no route calculation is available for the forecast day
- **THEN** the picker and the screen show the missing-data message and no navigation starts

#### Scenario: Truck without a route
- **WHEN** a calculation exists but assigned no route to the truck
- **THEN** the screen shows the missing-data message

### Requirement: Road route geometry
The path SHALL be the road-following geometry computed by the road-routing service for the calculated route, never straight connections. Each service stop SHALL have a position on the path, non-decreasing in driving order. A route whose geometry is inconsistent with its stops SHALL be rejected.

#### Scenario: Stops lie on the path
- **WHEN** a route of N service stops is returned
- **THEN** each stop's position is a vertex of the path and the positions do not decrease

#### Scenario: Invalid geometry
- **WHEN** the path has fewer than two points, a non-finite coordinate, or stop positions that decrease or do not match its legs
- **THEN** the route fails and the screen shows the route error with a retry action

### Requirement: Starting the route
The idle screen SHALL offer `Pradėti maršrutą`. While the route is being prepared the screen SHALL show `Ruošiamas maršrutas...`, and on success it SHALL enter navigation mode. It SHALL NOT mention files, parsing or route services.

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

### Requirement: Assumption disclosure
The documentation SHALL state that routes come from the route planning screen and are held only in server memory for a limited time, that the truck position is simulated, and what a Driver run needs.

#### Scenario: Documented
- **WHEN** a developer reads the driver documentation
- **THEN** it names the route source, its lifetime, the simulated parts and the steps before a Driver run
