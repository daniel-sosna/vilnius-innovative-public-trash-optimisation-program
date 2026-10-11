# Spec Delta

## Purpose

Present a reusable truck-following road animation without operational collection updates.

## ADDED Requirements

### Requirement: Shared truck-following page
`/admin/demo/truck/{truck_id}` SHALL use the shared administrator layout and display the title `Šiukšliavežės sekimas`. It SHALL validate the stored truck identity without showing its name. The page SHALL omit the illustrative-route description, collection/completion counters, color explanation, replay button and page-local return-to-Demo button. Administrator navbar navigation SHALL remain available.

#### Scenario: Open different trucks
- **WHEN** the administrator opens two valid truck links
- **THEN** both use the same road animation implementation without displaying their stored names

#### Scenario: Open directly or refresh
- **WHEN** a valid truck URL is opened directly or refreshed
- **THEN** the page initializes without depending on a prior in-memory planning run

#### Scenario: Missing truck context
- **WHEN** the identifier is invalid, missing from storage or its lookup fails
- **THEN** the page shows Lithuanian explanatory feedback without inventing a truck identity
- **AND** the shared navbar remains available

### Requirement: Road-following movement and camera
The truck SHALL move along road geometry supplied by the configured road-routing service. Its path SHALL NOT substitute straight connections between stops. The map camera SHALL follow the truck throughout movement and remain at its final position after completion. The animation SHALL move more slowly than the fixed 1.8-second segment animation, varying travel speed and stop durations, accelerating and decelerating at stops. Collected bins SHALL change visually without a textual collection counter.

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
- **THEN** the route starts on the roundabout at Geležinio Vilko / A. Goštauto
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

### Requirement: Animation has no operational side effects
Movement and collection SHALL remain demonstration state only. The page SHALL perform no GPS tracking, turn-by-turn navigation or database collection writes, and SHALL stop requests and animation when left. The global project date SHALL remain accessible and unlocked.

#### Scenario: Finish or abandon animation
- **WHEN** the animation completes or the administrator leaves before completion
- **THEN** no collection records, truck availability or stored routes are changed
- **AND** abandoned work cannot update another screen or lock its calendar
