# Spec Delta

## MODIFIED Requirements

### Requirement: Independent layer selection
The `Sluoksniai` section SHALL list all registered datasets with labeled checkboxes showing dataset names without descriptive paragraphs. Checking a layer SHALL display it; unchecking SHALL hide it. Multiple layers SHALL be selectable simultaneously without disabling one another. Dataset controls SHALL appear horizontally, wrapping only when available width requires it. Initially all checkboxes SHALL be unchecked. `Sąvartynai`, `Konteineriai` and `Gyventojų tankumas` SHALL be offered together.

#### Scenario: Enable the first layer
- **WHEN** an administrator checks `Sąvartynai`
- **THEN** its data loads and its points or clusters become visible

#### Scenario: Hide a visible layer
- **WHEN** an administrator unchecks a visible layer
- **THEN** its features and popup disappear while the basemap remains usable

#### Scenario: Select multiple registered datasets
- **WHEN** independently registered datasets are selected together
- **THEN** all selected layers remain enabled and disabling one preserves the others
- **AND** the shipped panel contains no placeholder future layers

#### Scenario: Start with no datasets selected
- **WHEN** the analytics page opens in a new session
- **THEN** all layer checkboxes are unchecked and no dataset is requested until enabled

#### Scenario: Enable population alongside existing points
- **WHEN** population is enabled while a point dataset is selected
- **THEN** polygons and the selected point dataset remain visible together
- **AND** toggling population preserves other dataset selections and any registered dataset filters

#### Scenario: Align dataset controls
- **WHEN** the dataset controls fit on one row
- **THEN** all checkbox and label centers align vertically, including beside the taller bin waste-type arrow

### Requirement: Layer identity and extension contract
Each layer SHALL have a stable ID, display name, dataset meaning, render kind, color-meaning legend entries and independent visibility state. Extensions SHALL be able to register point or non-point renderers without replacing the map screen or treating polygons/grids as markers. Active IDs and their dataset definitions SHALL be available to later in-app consumers without implementing an analytics assistant.

#### Scenario: Add another point definition
- **WHEN** a future point dataset is registered with its loader, appearance and feature details
- **THEN** it appears in the common selector and uses the existing clustering and expansion behavior

#### Scenario: Add a non-point renderer
- **WHEN** a polygon or grid renderer joins the layer contract
- **THEN** its visibility and loading use the common controls without point clustering being applied to its geometry

#### Scenario: Identify displayed datasets
- **WHEN** later application code reads the active layer selection
- **THEN** it can resolve each active ID to its dataset meaning independently of localized labels

#### Scenario: Identify the population dataset
- **WHEN** the population layer is selected
- **THEN** its active definition identifies declared-residence density on source polygons and a polygon render kind

## ADDED Requirements

### Requirement: Render the population grid as areas
The population layer SHALL display stored polygons as a translucent area overlay retaining merged shapes and holes. It SHALL NOT replace them with districts, centroid markers, clusters or smoothed heatmap blobs. Missing-density polygons SHALL have no visible fill or outline and SHALL NOT capture feature interactions.

#### Scenario: Display source geometry
- **WHEN** data includes single-hectare cells and merged polygons
- **THEN** their shaded areas follow the stored geometry and holes remain unfilled

#### Scenario: Missing-density remainder
- **WHEN** data includes the large remainder polygon with missing density
- **THEN** it adds no fill or outline, and clicking its interior opens no population popup
- **AND** it is not presented as zero population

### Requirement: Population density band colours
Displayed polygons SHALL use purple shades from light to dark for `<11`, `11–49`, `50–99`, `100–199` and `200+` residents per hectare. Suppressed density SHALL use the lowest band; numeric density SHALL determine its band directly. Polygon area and total residents SHALL NOT determine colour. Missing density SHALL remain outside the scale.

#### Scenario: Assign threshold boundaries
- **WHEN** polygons have numeric densities 10, 11, 49, 50, 99, 100, 199 and 200
- **THEN** their bands are respectively `<11`, `11–49`, `11–49`, `50–99`, `50–99`, `100–199`, `100–199` and `200+`

#### Scenario: Equal density on different areas
- **WHEN** two polygons have equal density and different areas or total residents
- **THEN** they use the same shade

#### Scenario: Suppressed density
- **WHEN** a polygon's resident estimate uses an assumed density for a suppressed value
- **THEN** its colour represents `<11`, without presenting the assumption as exact source density

### Requirement: Population density legend
The shared `Legenda` SHALL include five labelled purple swatches identifying population density bands in `gyv./ha`, plus a transparent missing-data entry. Colours SHALL match displayed polygons and coexist with existing dataset entries, including while population is unchecked.

#### Scenario: Read the density scale
- **WHEN** an administrator views the legend
- **THEN** entries identify `Gyventojų tankumas`, all five density bands and `gyv./ha`
- **AND** `Duomenų nėra (skaidru)` identifies transparent missing data alongside other dataset legends

#### Scenario: Narrow screen
- **WHEN** the page is viewed at 320 pixels wide
- **THEN** legend labels wrap inside the existing card without horizontal page scrolling

### Requirement: Population layer session lifecycle
Population SHALL use the existing independent layer lifecycle for loading, caching, loading/error/empty feedback and retry. Visibility changes and load completion SHALL preserve the camera and other datasets. Hiding SHALL close the population-owned popup. In-flight results SHALL NOT display or reopen a disabled layer.

#### Scenario: Disable during loading
- **WHEN** population is enabled and then disabled before the first read completes
- **THEN** the result can be cached but population features and popups remain hidden

#### Scenario: Re-enable cached data
- **WHEN** population is disabled and re-enabled after a successful read
- **THEN** its polygons reappear without another request or map recreation

#### Scenario: Hide the population popup
- **WHEN** population is disabled with its popup open
- **THEN** that popup closes and other selected datasets remain visible

#### Scenario: Preserve another dataset's popup
- **WHEN** population is disabled while another dataset's popup is open
- **THEN** that popup remains governed by its own dataset's existing behaviour

#### Scenario: Independent failure and retry
- **WHEN** population loading fails and its retry control is activated
- **THEN** only population is requested again, preserving camera and other datasets

#### Scenario: Empty response
- **WHEN** the enabled population layer receives an empty features array
- **THEN** its control displays `Duomenų nėra.` rather than loading or failure feedback

### Requirement: Point markers above population areas
Registered point markers and count groups SHALL remain visible and interactive above population polygons regardless of enable order. Clicking a marker over a polygon SHALL invoke only the marker's existing interaction. Clicking a displayed polygon away from markers SHALL open its details without moving the camera.

#### Scenario: Enable population after points
- **WHEN** population is enabled after a point dataset
- **THEN** point markers and counts remain above the purple fill

#### Scenario: Enable points after population
- **WHEN** a point dataset is enabled after population
- **THEN** its markers and counts appear above the purple fill

#### Scenario: Click an overlapping marker
- **WHEN** an administrator clicks a point or count marker over a population polygon
- **THEN** only its existing details, expansion or group interaction occurs
- **AND** no population popup replaces that result

#### Scenario: Inspect the population area
- **WHEN** an administrator clicks a displayed polygon away from point and count markers
- **THEN** its popup opens at the click location without panning or zooming
