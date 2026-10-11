# Spec Delta

## MODIFIED Requirements

### Requirement: Shared truck-following page
`/admin/routes/truck/{truck_id}?run_id={run_id}` SHALL use the shared administrator layout and display the title `Šiukšliavežės sekimas`. It SHALL resolve the selected truck within the calculated run without showing its name or substituting a shared fixture. The page SHALL omit the illustrative-route description, collection/completion counters, color explanation, replay button and page-local return-to-Demo button. Administrator navbar navigation SHALL remain available.

#### Scenario: Open different trucks
- **WHEN** the administrator opens two valid truck links
- **THEN** both use the same road animation implementation without displaying their stored names

#### Scenario: Open directly or refresh
- **WHEN** a valid truck URL is opened directly or refreshed
- **THEN** the page initializes using the selected truck’s cached calculated run, or shows actionable feedback when the run is missing or expired

#### Scenario: Missing truck context
- **WHEN** the identifier is invalid, missing from storage or its lookup fails
- **THEN** the page shows Lithuanian explanatory feedback without inventing a truck identity
- **AND** the shared navbar remains available

#### Scenario: Service stops and landfill returns
- **WHEN** the truck finishes a service leg or returns to unload at its landfill
- **THEN** service stops change collection color but landfill-return legs do not mark another bin collected


### Requirement: Road-following movement and camera
The truck SHALL move along its own calculated service-generated road geometry, including assigned landfill returns, rather than a shared hardcoded route. Its path SHALL NOT substitute straight connections between stops. The map camera SHALL follow the truck throughout movement and remain at its final position after completion. The animation SHALL move more slowly than the fixed 1.8-second segment animation, varying travel speed and stop durations, accelerating and decelerating at stops. Collected bins SHALL change visually without a textual collection counter.

The route line SHALL disappear behind the truck as it moves, retaining only the remaining road ahead. The full line SHALL be removed when the truck reaches the final stop.

#### Scenario: Hide traveled road
- **WHEN** the truck moves along a road leg
- **THEN** the visible line starts at its current interpolated position and continues through the remaining stops
- **AND** traveled portions stay hidden during collection pauses and the final line disappears at the last stop

#### Scenario: Follow the truck along roads
- **WHEN** the road route loads and the map is ready
- **THEN** the truck progresses along successive road segments while the camera follows its position
- **AND** stop pauses and speed changes vary across the route

#### Scenario: Start on the roundabout
- **WHEN** the truck-following page initializes
- **THEN** the truck starts at its calculated first road coordinate; a roundabout is used only when that calculated route starts there
- **AND** the truck and initial camera use that route's first snapped road coordinate

#### Scenario: Road service failure
- **WHEN** road geometry cannot be obtained
- **THEN** the screen shows actionable failure feedback without a straight-line replacement route

#### Scenario: Complete collection
- **WHEN** the truck reaches its last stop
- **THEN** it remains there with collected-bin visuals
- **AND** no completion text or replay button appears

#### Scenario: Narrow screen
- **WHEN** the page is viewed at 320 pixels wide
- **THEN** its title and primary map fit without horizontal page scrolling

#### Scenario: Service stops and landfill returns
- **WHEN** the truck finishes a service leg or returns to unload at its landfill
- **THEN** service stops change collection color but landfill-return legs do not mark another bin collected

