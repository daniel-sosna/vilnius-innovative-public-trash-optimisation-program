# Spec Delta

## ADDED Requirements

### Requirement: Read-only bin map response
`GET /map-analytics/bins` SHALL return an unpaginated GeoJSON FeatureCollection of all displayable stored bins in ascending ID order. Each Point SHALL use `[longitude, latitude]`, the bin ID as feature identity, and only `inventory_number`, `waste_type` and `capacity_m3` properties. Capacity SHALL be a JSON number or null. Nullable details SHALL remain JSON null, and reads SHALL preserve stored data and existing collection APIs.

#### Scenario: Read the complete bin registry
- **WHEN** an administrator requests the bin map response
- **THEN** every stored bin with displayable coordinates appears exactly once with its own ID and stored coordinates
- **AND** the response contains no pagination, site details, carrier data, history, schedules, predictions or unrelated metadata

#### Scenario: Preserve nullable and unexpected source values
- **WHEN** a bin has a null inventory number or capacity, or an unexpected waste-type string
- **THEN** its nullable values remain null and its waste-type string is returned unchanged
- **AND** a non-null capacity is returned as a number

#### Scenario: Read an empty bin registry
- **WHEN** no displayable bins exist
- **THEN** the endpoint succeeds with an empty features array

#### Scenario: Omit an unusable location
- **WHEN** a stored bin has a null, non-finite or out-of-range latitude or longitude
- **THEN** it is omitted from the map response without changing its record or adding an omitted-record management workflow
- **AND** other displayable bins remain available

### Requirement: Lithuanian bin marker details
Activating an individual bin marker SHALL open a lightweight map popup showing only `Inventorinis numeris`, `Atliekų rūšis` and `Talpa (m³)` details. Known waste types SHALL use their Lithuanian category labels; unexpected types SHALL display `Kitos atliekų rūšys`. Null details SHALL display `N/A`. Stored source strings SHALL remain unchanged.

#### Scenario: Inspect a recorded bin
- **WHEN** an administrator activates a blue, green or brown individual bin marker
- **THEN** the popup shows that bin's inventory number, localized waste type and capacity in cubic metres
- **AND** it exposes no internal IDs, address, carrier, site, history or other database fields

#### Scenario: Inspect missing details
- **WHEN** an activated bin has a null inventory number or capacity
- **THEN** the corresponding detail displays `N/A`, without rendering zero or the text null

#### Scenario: Inspect an unexpected waste type
- **WHEN** an administrator activates a gray bin with an unexpected waste-type string
- **THEN** its waste-type detail displays `Kitos atliekų rūšys` while its API and stored value retain the original string

### Requirement: Select individual bins from an overlap group
Activating a high-zoom bin overlap count marker SHALL open a compact scrollable popup list containing every bin represented by that marker exactly once. Each item SHALL identify a bin by its inventory number and localized waste-type label and SHALL be independently selectable. Selecting an item SHALL show that bin's three detail fields and provide `Atgal į sąrašą` to return to the same list.

#### Scenario: Inspect bins at identical coordinates
- **WHEN** an administrator activates a high-zoom group containing multiple bins at identical coordinates
- **THEN** the popup lists all represented bins, including bins of the same waste type
- **AND** selecting any item shows that bin's inventory number, waste type and capacity
- **AND** returning to the list allows another bin to be selected without moving the map

#### Scenario: Inspect nearby overlapping bins
- **WHEN** nearby bins have overlapping markers at high zoom and the administrator activates their group
- **THEN** all represented bins are individually reachable through the list without needing further zoom

#### Scenario: Browse a long group
- **WHEN** a represented group contains more bins than fit in the popup
- **THEN** its list scrolls internally and every item remains selectable by keyboard and pointer
- **AND** popup controls and text remain usable at 320-pixel screen widths

#### Scenario: Resolve nullable or duplicate item labels
- **WHEN** represented bins have duplicate or null inventory numbers
- **THEN** separate selectable items remain available for every bin, null inventory numbers display `N/A`, and each item opens its own corresponding details

### Requirement: Current bin popup membership
Bin group lists SHALL contain only bins matching the current waste filters. Hiding `Konteineriai`, changing its waste filters or navigating the map after opening a group SHALL close its popup and invalidate pending group interactions. Late results SHALL NOT reopen stale lists or details or move the map after their interaction has been invalidated.

#### Scenario: Open a filtered group
- **WHEN** paper/plastic bins are excluded and an administrator opens a remaining overlap group
- **THEN** the list contains only filter-matching bins and its item count matches the group's count

#### Scenario: Change filters with a list or detail open
- **WHEN** the administrator changes a waste filter while viewing a bin list or bin detail
- **THEN** the popup closes and no previous bin selection remains active

#### Scenario: Hide a layer during group retrieval
- **WHEN** the bin layer is disabled while its group list is being retrieved
- **THEN** the popup remains closed when retrieval completes
- **AND** disabling and immediately re-enabling the layer does not revive the prior interaction

#### Scenario: Navigate after opening an overlap group
- **WHEN** an administrator pans or zooms after opening a bin group list or its selected detail
- **THEN** the group popup closes so its membership cannot describe an outdated map group
