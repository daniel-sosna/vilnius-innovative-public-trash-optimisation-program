# Spec Delta

## Purpose

Let administrators explore Vilnius waste-related datasets on a large interactive map, beginning with the existing landfill catalog and its recorded location details.

## ADDED Requirements

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
