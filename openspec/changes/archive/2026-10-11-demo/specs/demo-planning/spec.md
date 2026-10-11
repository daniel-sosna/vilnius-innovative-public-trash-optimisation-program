# Spec Delta

## Purpose

Demonstrate the waste-planning workflow from real predicted service bins through explicitly illustrative truck routes, with visible stages and recoverable failures.

## ADDED Requirements

### Requirement: Accessible planning screen
Administrator navigation SHALL link to `/admin/demo`. The screen SHALL use the shared navbar, show selected and forecast dates, a prominent `Pradėti maršrutų planavimą` action above the map at the right, a large primary map, compact workflow feedback and subsequent truck results. Application labels SHALL be Lithuanian.

#### Scenario: Open the demonstration
- **WHEN** the administrator follows the Demo navigation link
- **THEN** the screen displays its action, date context and map without any assigned-truck table

#### Scenario: Use a narrow viewport
- **WHEN** Demo is viewed at 320 pixels wide
- **THEN** its map, action, status and results remain usable without horizontal page scrolling

### Requirement: Start a fresh sequential run
Starting SHALL clear previous predicted markers, routes, trucks and statuses while retaining the global date and map instance. Only one frontend run SHALL be active. Successful stages SHALL proceed automatically from prediction to visible bins, route calculation, route drawing and completed results.

#### Scenario: Restart after completion
- **WHEN** the administrator starts after a completed run
- **THEN** all previous run visuals and results clear before real prediction starts for the selected day
- **AND** the map instance is retained

#### Scenario: Prevent duplicate starts
- **WHEN** prediction, routing or drawing is active
- **THEN** the start action is disabled and repeated activation cannot launch another frontend pipeline

### Requirement: Honest prediction progress and markers
Prediction SHALL show animated indeterminate progress in the compact workflow stages throughout the real inference wait, without the separate prediction-duration explanatory text. After success, Demo SHALL highlight only due predicted bins with valid coordinates, show evaluated and mapped counts and disclose any bins excluded from visualization. Demo SHALL render individual bin markers without clustering and omit the Aptarnauti count label. Route calculation SHALL begin only after predicted markers have been presented on a ready map.

The predicted markers SHALL appear in a randomized order chosen once per run, adding batches of 1, 1, 1, 2, 2, 2, 4, 4, 4, 8, 8, 8, 16, 16, 16 and continuing with each doubled batch size repeated three times until the actual mapped total is reached. Existing markers SHALL remain visible as new batches appear. Delays SHALL decrease between batch-size groups while keeping early batches perceptible. The mapped count SHALL reflect the currently visible markers. The prediction stage and run lock SHALL remain active through this reveal. Reduced-motion preferences SHALL show the complete marker set without the accelerating animation.

#### Scenario: Wait for actual inference
- **WHEN** inference takes approximately five minutes
- **THEN** the prediction status remains active until the real result or a failure arrives, without fabricated progress percentages or predictions

#### Scenario: Display due bins
- **WHEN** prediction returns bins at fill levels 0 through 4
- **THEN** only level-3/4 bins with valid coordinates appear as selected markers
- **AND** unrelated bins are not highlighted and camera adjustment avoids repeated jumps

#### Scenario: Accelerate the predicted-bin reveal
- **WHEN** a successful prediction contains multiple mappable due bins
- **THEN** randomly ordered markers are added in batches of 1, 1, 1, 2, 2, 2, 4, 4, 4 and subsequent triplets of doubled batch sizes, continuing with shorter delays until every eligible marker is visible
- **AND** route calculation starts only after the final marker set has rendered
- **AND** leaving the screen cancels pending appearances

### Requirement: Replaceable road navigation results
Navigation SHALL accept the predicted mappable bins and forecast date, returning assigned truck identities, ordered coordinates and explicit stop/bin assignments. Paths SHALL follow the road network rather than straight connections between stops. Assignments SHALL use up to 150 available stored trucks with nonempty groups and SHALL NOT claim fleet optimization or capacity feasibility. Demo SHALL omit the schematic-route disclaimer requested for removal. Assignments SHALL reference input bins and available nondeleted stored trucks.

#### Scenario: Keep prediction and routing connected
- **WHEN** road navigation succeeds
- **THEN** every routed bin belongs to the prediction input, each mappable input bin is assigned once, and the returned truck names correspond to stored trucks
- **AND** repeated requests with identical inputs and fleet produce identical assignments

#### Scenario: No available trucks
- **WHEN** no eligible stored truck exists
- **THEN** navigation reports an actionable failure, preserves predicted markers and fabricates no truck result

### Requirement: Progressive route drawing
Routes SHALL grow smoothly from start to finish instead of appearing complete immediately. Different trucks SHALL have distinguishable restrained colors, while predicted markers and map labels remain understandable. Drawing SHALL have a finite duration and handle a one-stop route without leaving the run pending.

#### Scenario: Draw multiple routes
- **WHEN** navigation returns multiple routes
- **THEN** partial paths extend along their ordered coordinates and all drawing completes before truck results appear

#### Scenario: One-stop route
- **WHEN** an assigned truck has only one stop
- **THEN** its location is presented meaningfully and drawing completes without requiring an artificial extra bin

### Requirement: Compact stage feedback
The workflow area SHALL distinguish active, completed and failed stages for bin prediction, route calculation and route drawing. An active stage SHALL show a loading indicator. Completion SHALL identify routes as ready, and errors SHALL identify the failed stage without marking it successful.

#### Scenario: Route calculation follows prediction
- **WHEN** predicted markers are visible and navigation is pending
- **THEN** bin selection is shown completed and route calculation active

#### Scenario: Route drawing follows calculation
- **WHEN** routes have returned and drawing is underway
- **THEN** prediction and calculation are completed while drawing is active

### Requirement: Reveal assigned trucks after drawing
The truck table SHALL appear only after all route drawing finishes, with one row per assigned truck showing its stored name, route label and assigned stop/bin counts. The table SHALL be paginated with a maximum of five rows per page, retaining the complete map while changing pages and resetting to page one for a new run. Rows SHALL be keyboard-accessible links to `/admin/demo/truck/{truck_id}` and associate each route with its visual color.

#### Scenario: Reveal and activate results
- **WHEN** the last route finishes drawing
- **THEN** the table becomes visible with accurate counts derived from assignments
- **AND** activating any truck row opens its driving-demo route

### Requirement: Recover from empty results and failures
Empty predictions SHALL stop the pipeline with `Šiai dienai aptarnauti skirtų konteinerių nerasta.` and no navigation request. Prediction, navigation or drawing failures SHALL stop loading, unlock date/start controls and permit restart. Navigation failures SHALL retain predicted markers; no failure SHALL reveal successful truck results.

#### Scenario: No due bins
- **WHEN** real prediction selects zero bins
- **THEN** the empty message appears, navigation is not called and no demo bins are invented

#### Scenario: Missing coordinates for every due bin
- **WHEN** bins are due but none can be mapped
- **THEN** Demo reports missing usable coordinates, does not describe the result as zero due bins, and does not start navigation

#### Scenario: Fail a stage
- **WHEN** prediction, navigation or route drawing fails or reaches its finite timeout
- **THEN** its error is shown, active controls unlock and restart is possible
- **AND** a navigation failure retains predicted markers

### Requirement: Discard abandoned and obsolete work
Leaving Demo SHALL stop local animations and requests, release the calendar lock and prevent late responses from restoring visuals or results. Starting a new run or changing the date after a terminal result SHALL invalidate obsolete outputs. Backend inference already underway SHALL not be represented as forcibly cancelled unless it actually stops.

#### Scenario: Leave during inference or drawing
- **WHEN** the administrator navigates away during an active stage
- **THEN** local work is cleaned up and a late completion cannot update the abandoned screen or relock its calendar

#### Scenario: Change date after completion
- **WHEN** a completed run exists and the administrator changes the global date
- **THEN** previous markers, routes and results clear without starting another run automatically

#### Scenario: Obsolete response after restart
- **WHEN** a response from an abandoned run arrives during a newer run
- **THEN** it cannot alter the newer run's stage, visuals, results or date lock

#### Scenario: Road service failure
- **WHEN** road geometry cannot be calculated
- **THEN** navigation reports an actionable error and retains selected-bin markers
- **AND** no straight-line replacement path is returned

#### Scenario: Browse the truck results
- **WHEN** a completed run assigns 150 trucks
- **THEN** the result table contains 30 pages with five trucks per page
- **AND** changing pages preserves all route drawings on the map
