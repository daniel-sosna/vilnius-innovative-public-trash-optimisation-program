# Spec Delta

## MODIFIED Requirements

### Requirement: Replaceable road navigation results
Navigation SHALL optimize the current predicted mappable bins per carrier using their predicted loads, available stored trucks, capacity limits and landfill reloads. Paths SHALL follow roads in the optimized visit order. At most 150 eligible trucks SHALL be used. The response SHALL report unserved bins separately. Demo SHALL omit the schematic-route disclaimer. Inputs SHALL remain unchanged and no collection or route plans SHALL be saved.

#### Scenario: Keep prediction and routing connected
- **WHEN** road navigation succeeds
- **THEN** every routed bin belongs to the prediction input, assigned and unserved bins partition that input exactly once, and the returned truck names correspond to stored trucks
- **AND** repeated requests with identical inputs and fleet produce identical assignments

#### Scenario: No available trucks
- **WHEN** no eligible stored truck exists
- **THEN** navigation reports unserved bins with an actionable reason and fabricates no truck result

#### Scenario: Carrier or capacity prevents collection
- **WHEN** a stop has no eligible matching-carrier truck or its load exceeds every matching truck capacity
- **THEN** its bin identities and reason appear as unserved while other feasible truck assignments remain available

#### Scenario: Landfill reloads
- **WHEN** a truck receives multiple trips
- **THEN** the road path returns to its assigned landfill between trips and after its last trip
- **AND** the service-stop list contains only the predicted bins being collected


### Requirement: Accessible planning screen
Administrator navigation SHALL show one `Maršrutai` link to `/admin/routes`, using the prediction and navigation workflow. The separate stored-plan screen SHALL be omitted. /admin/demo SHALL redirect to /admin/routes. The screen SHALL use the shared navbar, show selected and forecast dates, a prominent `Pradėti maršrutų planavimą` action above the map at the right, a large primary map, compact workflow feedback and subsequent truck results. Application labels SHALL be Lithuanian.

#### Scenario: Open the demonstration
- **WHEN** the administrator follows the Maršrutai navigation link
- **THEN** the screen displays its action, date context and map without any assigned-truck table

#### Scenario: Use a narrow viewport
- **WHEN** Demo is viewed at 320 pixels wide
- **THEN** its map, action, status and results remain usable without horizontal page scrolling


### Requirement: Start a fresh sequential run
Starting SHALL clear previous predicted markers, routes, trucks and statuses while retaining the global date and map instance. Only one frontend run SHALL be active. Successful stages SHALL proceed automatically from prediction to visible bins, route calculation and immediate truck results. The planning map SHALL remain visible during and after navigation, retaining predicted markers and omitting all-route drawing. The truck table shell SHALL appear immediately after prediction finishes.

#### Scenario: Restart after completion
- **WHEN** the administrator starts after a completed run
- **THEN** all previous run visuals and results clear before real prediction starts for the selected day
- **AND** the map instance is retained

#### Scenario: Prevent duplicate starts
- **WHEN** prediction, marker appearance or routing is active
- **THEN** the start action is disabled and repeated activation cannot launch another frontend pipeline


### Requirement: Compact stage feedback
The workflow area SHALL distinguish active, completed and failed bin prediction. After prediction, the truck table SHALL contain the loading indicator while marker appearance and route calculation are pending. Completion SHALL identify routes as ready, and errors SHALL identify failure without marking it successful.

#### Scenario: Route calculation follows prediction
- **WHEN** predicted markers are visible and navigation is pending
- **THEN** bin prediction is shown completed and the truck table contains an active route-calculation spinner

#### Scenario: Route drawing follows calculation
- **WHEN** routes have returned and navigation calculation is complete
- **THEN** prediction and calculation are completed while the truck table contains the calculated rows and the planning map remains visible


### Requirement: Reveal assigned trucks after drawing
The truck table SHALL appear immediately after prediction finishes, with a loading row while marker appearance or navigation is pending. Once navigation finishes, it SHALL show one row per assigned truck with its stored name, route label and assigned stop/bin counts. Empty results or failures SHALL replace the loading row with explicit feedback. The table SHALL be paginated with a maximum of five rows per page, without displaying a combined route map while changing pages and resetting to page one for a new run. Rows SHALL be keyboard-accessible links to `/admin/routes/truck/{truck_id}?run_id={run_id}` and associate each route with its visual color.

#### Scenario: Show the table while planning
- **WHEN** prediction finishes and marker appearance or navigation is pending
- **THEN** the table headers and loading row are visible below the map
- **AND** the route-calculation spinner appears inside the table rather than the prediction feedback

#### Scenario: Reveal and activate results
- **WHEN** navigation calculation finishes
- **THEN** the existing table replaces its loading row with assigned trucks and accurate counts derived from assignments
- **AND** activating any truck row opens its driving-demo route


## REMOVED Requirements

### Requirement: Progressive route drawing
**Reason**: The planning screen shows the truck table immediately after navigation instead of drawing all paths.
**Migration**: Open a truck row to view its calculated road path on the tracking screen.
