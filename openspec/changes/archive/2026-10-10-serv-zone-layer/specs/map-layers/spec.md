# Spec Delta

## MODIFIED Requirements

### Requirement: Independent layer selection
The `Sluoksniai` section SHALL list all registered datasets with labeled checkboxes showing dataset names without descriptive paragraphs. Checking a layer SHALL display it; unchecking SHALL hide it. Multiple layers SHALL be selectable simultaneously without disabling one another. Dataset controls SHALL appear horizontally, wrapping only when available width requires it. Initially all checkboxes SHALL be unchecked. `Sąvartynai`, `Konteineriai`, `Gyventojų tankumas` and `Aptarnavimo zonos` SHALL be offered together.

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

#### Scenario: Enable all current datasets
- **WHEN** all four datasets are selected
- **THEN** service zones, population polygons, landfill markers and matching bin markers or groups remain visible together
- **AND** toggling zones preserves the other selections and bin filters

### Requirement: Layer identity and extension contract
Each layer SHALL have a stable ID, display name, dataset meaning, render kind, color-meaning legend entries and independent visibility state. The visual-only service-zone context layer SHALL use an empty legend entry list. Extensions SHALL be able to register point or non-point renderers without replacing the map screen or treating polygons/grids as markers. Active IDs and their dataset definitions SHALL be available to later in-app consumers without implementing an analytics assistant.

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

#### Scenario: Identify the service-zone context
- **WHEN** the service-zone layer is selected
- **THEN** its active definition identifies stored waste collection service areas with a polygon render kind
- **AND** its polygons are not included in point clustering

### Requirement: Extensible color legend
Each registered dataset SHALL define its color meanings, except `Aptarnavimo zonos`, which SHALL contribute no legend entries. The screen SHALL display all registered color meanings in a labeled `Legenda` section after the layer checkboxes in the shared card underneath the map. Color swatches SHALL have accompanying text, and the legend SHALL support multiple entries per dataset without assuming point geometry. Landfill pins and clusters SHALL be black, matching the `Sąvartynai` legend entry. Bin entries SHALL identify category and group colors.

#### Scenario: Identify landfill color
- **WHEN** the analytics screen opens
- **THEN** a black swatch labeled `Sąvartynai` appears under the map
- **AND** enabled landfill pins and clusters use that black color

#### Scenario: Extend color meanings
- **WHEN** a dataset supplies multiple color categories or a non-point renderer with legend entries
- **THEN** its color meanings appear through the common legend
- **AND** a point definition can color individual features by recorded properties without replacing the map page
- **AND** the bin categories are included without adding district or other future datasets

#### Scenario: Distinguish bin categories from counts
- **WHEN** the administrator views the legend
- **THEN** labeled blue, green and brown swatches identify the known bin waste categories
- **AND** gray identifies `Kitos atliekų rūšys` and a separately labeled neutral swatch identifies `Konteinerių grupė`

#### Scenario: Preserve the legend when zones are registered
- **WHEN** the page opens or service zones are toggled
- **THEN** existing landfill, bin and population legend entries remain unchanged
- **AND** no service-zone legend, metric scale or additional analytics panel is added

## ADDED Requirements

### Requirement: Uniform service-zone context polygons
Enabling `Aptarnavimo zonos` SHALL display all returned service-zone polygons with one shared translucent fill color and clearly visible boundaries, retaining stored shapes and holes. The basemap and other enabled datasets SHALL remain readable. Disabling the layer SHALL hide its fills, outlines and text together.

#### Scenario: Display the supplied zones
- **WHEN** the layer receives the supplied five stored zones
- **THEN** all five polygons use the same fill color and adjacent zones are distinguishable by boundaries
- **AND** no metric-based or per-zone color scheme is applied

#### Scenario: Hide every zone visual
- **WHEN** the administrator unchecks `Aptarnavimo zonos`
- **THEN** zone fills, boundaries and names disappear together while the basemap and other selected layers remain available

### Requirement: Interior service-zone names
Zone names SHALL appear as map text using the API's `zone_name`, without hover or click. Placement SHALL favor each polygon's visual interior, including irregular shapes and holes, rather than blindly using bounding-box centers. Text SHALL remain readable with a subtle halo, adapt to zoom and avoid unnecessary overlap; unsuitable zoom or collisions may suppress labels.

#### Scenario: Read zones at the city overview
- **WHEN** the supplied zones are displayed at the initial Vilnius view
- **THEN** every zone can be identified by a readable Lithuanian name within its polygon, without interaction

#### Scenario: Irregular polygon or hole
- **WHEN** a zone's bounding-box center lies outside its filled area
- **THEN** its visible text anchor is placed inside the filled polygon instead

#### Scenario: Change zoom
- **WHEN** the administrator zooms through city overview and close views
- **THEN** visible labels retain suitable size and readability, with labels hidden when space is unsuitable
- **AND** boundary-adjacent text does not create unnecessary overlap

### Requirement: Service zones are visual only
Service-zone polygons, outlines and labels SHALL NOT open popups, select zones, show details, capture clicks or create a zone-specific interactive cursor. Existing marker, group and population interactions SHALL retain their behavior through zone visuals.

#### Scenario: Click only a service zone
- **WHEN** the administrator clicks a zone where no interactive data feature exists
- **THEN** no zone popup, selection or detail card appears and the camera does not move

#### Scenario: Click a marker within a zone
- **WHEN** a landfill or bin marker or count group is activated inside a zone
- **THEN** only that dataset's existing popup, group selection or expansion occurs

#### Scenario: Click population beneath zone text
- **WHEN** a displayed population polygon is clicked at a zone label, away from interactive markers
- **THEN** the population details open normally and the zone label does not suppress or replace them

### Requirement: Service-zone session lifecycle
Zones SHALL use the existing independent lazy-loading, pending-read sharing, successful session caching, retry and empty/error/loading feedback. Their lifecycle SHALL preserve the map instance, camera, other dataset filters and unrelated popups. All application-provided feedback SHALL use existing Lithuanian wording.

#### Scenario: Open without zones selected
- **WHEN** the analytics page starts
- **THEN** `Aptarnavimo zonos` is unchecked and no service-zone request is made

#### Scenario: Disable during first load
- **WHEN** zones are disabled before their request completes
- **THEN** the result can be cached but no zone fills, outlines or labels appear
- **AND** re-enabling during the pending request does not duplicate it

#### Scenario: Re-enable loaded zones
- **WHEN** successfully loaded zones are disabled and enabled again in the session
- **THEN** all zone visuals reappear without another request or map recreation

#### Scenario: Independent failure and retry
- **WHEN** zones fail to load and the administrator activates their retry
- **THEN** only zone data is requested again, and other layers and the camera remain usable
- **AND** feedback uses `Nepavyko įkelti sluoksnio.` and `Bandyti dar kartą`

#### Scenario: Empty zone response
- **WHEN** the enabled layer receives an empty features array
- **THEN** its control displays `Duomenų nėra.` and no zone visuals appear

#### Scenario: Preserve unrelated state
- **WHEN** zones are toggled after panning and zooming with bin filters and another dataset's popup active
- **THEN** the camera, filters, other selections and unrelated popup are preserved

### Requirement: Service-zone ordering across current layers
Zones SHALL provide background geographic context with fill below population areas and point data. Zone outlines and names SHALL remain legible with population enabled, while point markers and count groups remain above zone visuals. These relationships SHALL hold independently of enable order and request completion order.

#### Scenario: Zones enabled last
- **WHEN** zones load after landfills, bins and population
- **THEN** their fill remains behind the data, their boundaries and names remain legible and point data remains above them

#### Scenario: Zones enabled first
- **WHEN** other datasets load after zones
- **THEN** the same ordering and readability are preserved

#### Scenario: Layer combinations on a narrow screen
- **WHEN** any combination of the four datasets is enabled at 320-pixel width
- **THEN** the existing map and controls remain usable without page-wide horizontal scrolling
- **AND** zone selection adds only its checkbox and normal lifecycle feedback to the existing screen
