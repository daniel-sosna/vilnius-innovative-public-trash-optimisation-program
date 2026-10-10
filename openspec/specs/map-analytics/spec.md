# map-analytics Specification

## Purpose

Let administrators explore Vilnius waste-related datasets on a large interactive map, beginning with the existing landfill catalog and its recorded location details.

## Requirements

### Requirement: Admin map analytics navigation
The shared admin navbar SHALL include `Žemėlapio analitika`, opening `/admin/map-analytics`. The route SHALL support direct opening and refresh and retain existing responsive navigation behavior.

#### Scenario: Open analytics through navigation
- **WHEN** an administrator selects `Žemėlapio analitika`
- **THEN** the analytics screen opens inside the existing admin layout and its navbar link is active

#### Scenario: Open a deep link
- **WHEN** `/admin/map-analytics` is opened or refreshed directly
- **THEN** the screen loads without requiring prior navigation

### Requirement: Large interactive Vilnius map
The screen SHALL be dominated by a map initially centered on Vilnius. Users SHALL be able to pan and zoom with mouse, touch and keyboard, use labeled zoom controls, and activate displayed features. One card underneath the map SHALL contain the `Sluoksniai` heading and layer checkboxes, followed by the `Legenda` heading and labeled color swatches. Its layer list SHALL scroll internally when necessary. The card SHALL remain usable at 320-pixel widths without obscuring the map.

#### Scenario: Explore the city
- **WHEN** the screen opens on desktop
- **THEN** the map occupies most of the available content area and supports pan, zoom and feature interaction
- **AND** the map fills the content width and the shared layer/legend card appears underneath it

#### Scenario: Scroll a long layer list
- **WHEN** registered layers exceed the available list height
- **THEN** the list scrolls within the card while both headings and the legend remain reachable and the map height stays fixed

#### Scenario: Use a narrow screen
- **WHEN** the screen is viewed at 320 pixels wide
- **THEN** navigation, layer controls, map controls and popup content remain reachable without page-wide horizontal scrolling
- **AND** the shared card stays below the map with both sections visible

#### Scenario: Focus through pointer and keyboard interaction
- **WHEN** an administrator clicks or touches the map canvas
- **THEN** the canvas does not display a focus outline
- **AND** keyboard navigation still provides a visible focus indicator

### Requirement: Configurable and recoverable basemap
The screen SHALL use the existing frontend `VITE_MAP_STYLE_URL` configuration. Missing configuration or unavailable map resources SHALL produce a clear Lithuanian map error and an appropriate recovery action. A landfill-data failure SHALL NOT prevent use of the basemap.

#### Scenario: Change the map style
- **WHEN** the frontend starts or builds with another valid `VITE_MAP_STYLE_URL`
- **THEN** analytics uses that configured style without a component change

#### Scenario: Recover from a map-resource failure
- **WHEN** configured map resources fail to load
- **THEN** the map area shows a Lithuanian error and `Bandyti dar kartą`

#### Scenario: Report missing configuration
- **WHEN** the map style setting is missing or invalid
- **THEN** the map area identifies the configuration problem in Lithuanian rather than silently selecting another style

### Requirement: Read-only landfill map response
`GET /map-analytics/landfills` SHALL return a GeoJSON FeatureCollection of stored landfills in ascending ID order. Each Point SHALL use `[longitude, latitude]`, its landfill ID as feature identity, and only name, operator, address and coordinate quality as detail properties. Nullable properties SHALL remain JSON null. Reads SHALL preserve existing records and catalog API behavior.

#### Scenario: Read the seeded facilities
- **WHEN** the endpoint reads the existing three migration-seeded facilities
- **THEN** it returns three uniquely identified Point features at their stored coordinates with the four specified detail properties
- **AND** it returns no truck assignments, collection history or unrelated source metadata

#### Scenario: Read an empty catalog
- **WHEN** no displayable landfill records exist
- **THEN** the endpoint returns a successful FeatureCollection with an empty features array

### Requirement: Omit landfill markers with null coordinates
A landfill with either latitude or longitude null SHALL have no marker and SHALL be omitted from the map response. Its stored record SHALL remain unchanged. The screen SHALL NOT add an omitted-record count or special management workflow.

#### Scenario: Skip an unknown location
- **WHEN** a landfill has a null latitude or longitude
- **THEN** the map response omits that feature and other landfill markers remain available

### Requirement: Identifiable landfill details
Activating an individual landfill marker SHALL open a lightweight map popup identifying that facility by a name heading and showing only operator and address detail rows. The popup SHALL omit `Pavadinimas` and `Koordinačių tikslumas` rows. Displayed nulls SHALL appear as `N/A`. Hiding the landfill layer SHALL close its popup.

#### Scenario: Inspect one facility
- **WHEN** an administrator activates an individual landfill marker
- **THEN** a popup identifies that facility and shows its recorded details, with `N/A` for nullable values

#### Scenario: Show compact details
- **WHEN** a facility popup is displayed
- **THEN** its name appears once as the heading, with operator and address underneath
- **AND** recorded coordinate quality remains in the API without appearing as a popup row

### Requirement: Correct Lithuanian interface
Application-provided text SHALL use correct Lithuanian, including `Žemėlapio analitika`, `Sluoksniai`, `Sąvartynai`, popup labels, loading/error/empty states and control labels. English descriptive text in the three known seed records SHALL have Lithuanian presentation while preserving proper names, meaning and stored data. `N/A` SHALL remain the missing-value token.

#### Scenario: Inspect the existing English source descriptions
- **WHEN** a seeded facility popup is displayed
- **THEN** its displayed name, operator and address descriptions are presented in Lithuanian with organization names and address identity retained
- **AND** neither the database nor existing catalog responses are rewritten for translation

#### Scenario: See recoverable feedback
- **WHEN** a layer is loading, empty or has failed
- **THEN** its feedback uses Lithuanian text, and a failed read exposes a labeled retry action

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

### Requirement: Read-only population map response
`GET /map-analytics/population-cells` SHALL return an unpaginated GeoJSON FeatureCollection of stored population polygons in ascending ID order. Each feature SHALL use the polygon ID, Polygon geometry in longitude/latitude with all rings, and only `density_per_ha`, `suppressed`, `area_ha` and `residents` properties. Numeric values SHALL be JSON numbers and suppression SHALL be a boolean.

#### Scenario: Read the stored grid
- **WHEN** the population map response is requested
- **THEN** each stored polygon appears exactly once with its ID, outer ring and holes
- **AND** merged polygons retain their geometry and area without subdivision
- **AND** no bin allocation, bounding-box fields, collection records or unrelated metadata is returned

#### Scenario: Empty population table
- **WHEN** no population polygons are stored
- **THEN** the response succeeds with an empty features array

### Requirement: Preserve population density uncertainty
The response SHALL retain numeric density as its stored value. Suppressed density SHALL have `density_per_ha: null`, `suppressed: true` and the stored estimated `residents`. Missing density SHALL have `density_per_ha: null`, `suppressed: false` and `residents: null`, rather than exposing a placeholder zero as a known population.

#### Scenario: Numeric density on a merged polygon
- **WHEN** a polygon stores density 14, area 3 hectares and estimated residents 42
- **THEN** its response preserves those numbers and suppression false

#### Scenario: Suppressed density
- **WHEN** a polygon represents `<11` with area 1 hectare and stored estimated residents 5
- **THEN** its response contains null density, suppression true, area 1 and residents 5

#### Scenario: Missing density
- **WHEN** a polygon has missing density, suppression false and stored residents 0
- **THEN** its response contains null density and null residents while retaining geometry and area
- **AND** its database values remain unchanged

### Requirement: Population reads do not rebuild data
Population map reads SHALL use the existing read-only collection snapshot, preserve stored data and require no source-file access or rebuild. Database failures SHALL follow the existing collection-read error contract rather than being reported as successful empty datasets.

#### Scenario: Read without the source file
- **WHEN** stored polygons exist and their source file is unavailable
- **THEN** reads remain available and neither population table changes

#### Scenario: Database unavailable
- **WHEN** the population dataset cannot be read
- **THEN** the endpoint reports a failed read rather than a successful empty response

### Requirement: Lithuanian population polygon details
Activating a displayed population polygon SHALL open a lightweight popup headed `Gyventojų tankumas`, with `Tankumas (gyv./ha)`, `Plotas (ha)` and `Apytikslis gyventojų skaičius`. Numeric density SHALL display its recorded value; suppressed density SHALL display `<11`. Area and estimated residents SHALL use Lithuanian number formatting, rounded to at most two and one decimal places respectively.

#### Scenario: Inspect numeric-density data
- **WHEN** an administrator activates a polygon with density 14, area 3 and estimated residents 42
- **THEN** the popup shows density 14, area 3 hectares and approximately 42 residents as distinct quantities

#### Scenario: Inspect merged geometry
- **WHEN** an administrator activates a merged polygon
- **THEN** its details use the full polygon's stored area and estimated residents, without assuming a 1-hectare square

### Requirement: Explain suppressed resident estimates
A suppressed polygon's popup SHALL distinguish the source bound `<11` from the assumption used for its estimated resident total. For positive area it SHALL display the applied estimate density obtained from stored residents divided by area. For zero area it SHALL explain the estimate without dividing by zero or inventing an applied density.

#### Scenario: Default assumption
- **WHEN** a suppressed polygon stores area 2 and estimated residents 10
- **THEN** the density row shows `<11` and an explanation identifies the estimate assumption as 5 residents per hectare

#### Scenario: Different assumption
- **WHEN** a suppressed polygon stores area 2 and estimated residents 20
- **THEN** the explanation identifies the applied estimate density as 10, rather than hardcoding the default 5

#### Scenario: Zero-area polygon
- **WHEN** a suppressed polygon has area 0
- **THEN** the popup identifies the total as estimated without displaying invalid or invented assumption values

### Requirement: Identify population source meaning
Population details SHALL identify the data as based on declared residence and resident totals as estimates. The interface SHALL NOT claim live population, observed headcounts, district totals or bin service catchments. It SHALL NOT invent a source year when none is stored.

#### Scenario: Explain the overlay
- **WHEN** an administrator opens a population popup
- **THEN** Lithuanian text explains declared residence and estimated totals
- **AND** it makes no claim about current physical presence or a bin's residents
