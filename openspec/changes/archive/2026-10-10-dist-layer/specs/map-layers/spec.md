# Spec Delta

## MODIFIED Requirements

### Requirement: Independent layer selection
The `Sluoksniai` section SHALL list all registered datasets with labeled checkboxes showing dataset names without descriptive paragraphs. Checking a layer SHALL display it; unchecking SHALL hide it. Multiple layers SHALL be selectable simultaneously without disabling one another. Dataset controls SHALL appear horizontally, wrapping only when available width requires it. Initially all checkboxes SHALL be unchecked. `Sąvartynai`, `Konteineriai`, `Gyventojų tankumas` and `Seniūnijos` SHALL be offered together.

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

#### Scenario: Select the district overlay with every current dataset
- **WHEN** all four shipped layer checkboxes are selected
- **THEN** all four datasets remain enabled and visible together
- **AND** district visibility changes preserve other selections and bin category filters

#### Scenario: Preserve the existing screen
- **WHEN** the new district option is displayed
- **THEN** the current map-first layout, shared controls card and existing legends remain in place
- **AND** the added control remains reachable at 320-pixel widths


### Requirement: Layer identity and extension contract
Each layer SHALL have a stable ID, display name, dataset meaning, render kind, declared color meanings where applicable and independent visibility state. The named district context overlay SHALL be allowed an empty legend. Extensions SHALL be able to register point or non-point renderers without replacing the map screen or treating polygons/grids as markers. Polygon definitions SHALL support fill styling, outline styling, optional labels and optional interaction independently of point clustering. Active IDs and their dataset definitions SHALL be available to later in-app consumers without implementing an analytics assistant.

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

#### Scenario: Distinguish polygon interaction policies
- **WHEN** the district and population polygon datasets are registered together
- **THEN** districts provide areas and boundaries without labels or interaction while population retains its existing feature details
- **AND** district rendering is not identified as point markers or clusters


### Requirement: Extensible color legend
Each registered dataset SHALL define its color meanings where a legend is applicable; the named district context overlay SHALL provide no legend entries. The screen SHALL display all registered legend entries in a labeled `Legenda` section after the layer checkboxes in the shared card underneath the map. Color swatches SHALL have accompanying text, and the legend SHALL support multiple entries per dataset without assuming point geometry. Landfill pins and clusters SHALL be black, matching the `Sąvartynai` legend entry. Bin entries SHALL identify category and group colors.

#### Scenario: Identify landfill color
- **WHEN** the analytics screen opens
- **THEN** a black swatch labeled `Sąvartynai` appears under the map
- **AND** enabled landfill pins and clusters use that black color

#### Scenario: Extend color meanings
- **WHEN** a dataset supplies multiple color categories or a non-point renderer
- **THEN** its color meanings appear through the common legend
- **AND** a point definition can color individual features by recorded properties without replacing the map page
- **AND** the bin categories are included without adding district or other future datasets

#### Scenario: Distinguish bin categories from counts
- **WHEN** the administrator views the legend
- **THEN** labeled blue, green and brown swatches identify the known bin waste categories
- **AND** gray identifies `Kitos atliekų rūšys` and a separately labeled neutral swatch identifies `Konteinerių grupė`

#### Scenario: Preserve legends when adding districts
- **WHEN** Seniūnijos is registered or toggled
- **THEN** no district swatches or new analytics legend section are added
- **AND** all existing landfill, bin and population legend entries remain available


## ADDED Requirements

### Requirement: District layer independent session lifecycle
Seniūnijos SHALL use the shared independent layer loading, caching, visibility and retry lifecycle. It SHALL start unchecked, load only on first enable, share pending requests and reuse successful data during the page session. Toggling SHALL preserve the camera, map instance, other layers, bin filters and unrelated popups.

#### Scenario: First enable and cached re-enable
- **WHEN** Seniūnijos is enabled, successfully loaded, disabled and enabled again
- **THEN** its fills and outlines reappear using cached data without another dataset request or map recreation

#### Scenario: Disable during a pending read
- **WHEN** Seniūnijos is unchecked before its request completes
- **THEN** the response can be cached but no district fill or outline becomes visible

#### Scenario: Hide all district rendering
- **WHEN** Seniūnijos is unchecked while all datasets are enabled and another dataset has an open popup
- **THEN** every district fill and boundary disappears
- **AND** other datasets, their filters, the camera and the unrelated popup retain their current state

#### Scenario: Empty and failed district reads
- **WHEN** an enabled district read is empty or fails
- **THEN** its existing controls distinguish empty data from failure and provide retry only for failure
- **AND** retry requests only district data while the basemap and other layers remain usable

### Requirement: Distinct stable district colors and boundaries
Each district in the supplied 21-district catalog SHALL have a distinct deterministic vibrant color, a translucent fill and a clear outline that make neighboring areas easy to distinguish. Color assignment SHALL remain stable across response ordering, map renders and visibility toggles. Streets, basemap text and other enabled datasets SHALL remain readable.

#### Scenario: Display the supplied catalog
- **WHEN** Seniūnijos is enabled at a city overview zoom
- **THEN** all 21 district areas have distinct colors and visible shared boundaries
- **AND** streets and map labels remain readable through or above the translucent overlay

#### Scenario: Stable colors across ordering and renders
- **WHEN** the same districts are returned in another order or the overlay is re-rendered or toggled
- **THEN** each district retains its assigned color

### Requirement: District overlay omits name labels
Seniūnijos SHALL display district areas and boundaries without rendering district name labels. This behavior SHALL hold at every zoom level and visibility toggle. The layer option SHALL remain `Seniūnijos`.

#### Scenario: Enable districts without names
- **WHEN** the Seniūnijos layer is enabled
- **THEN** its colored fills and outlines appear without district name text

#### Scenario: Zoom or re-enable the overlay
- **WHEN** the map zoom changes or Seniūnijos is hidden and re-enabled
- **THEN** district names remain absent from the overlay
- **AND** district fills and boundaries retain their styling

### Requirement: District overlay has no feature interaction
District fills and outlines SHALL NOT select districts, open popups or detail cards, capture polygon clicks or add hover interaction. Enabling, disabling or interacting over the overlay SHALL preserve point and population feature interactions. District areas and boundaries SHALL NOT block population clicks.

#### Scenario: Click district context alone
- **WHEN** an administrator clicks a district fill or outline with no other interactive feature at that position
- **THEN** no district selection, popup or detail card opens and the camera does not change because of the district layer

#### Scenario: Click a point above districts
- **WHEN** an administrator activates a landfill, bin marker or count group over a district
- **THEN** only that point dataset's existing interaction occurs
- **AND** cluster membership and counts remain governed by the point dataset

#### Scenario: Click population over district context
- **WHEN** a displayed population polygon is activated over a district area away from point markers
- **THEN** the existing population details open and district rendering does not suppress that interaction

### Requirement: District rendering order is independent of load order
District fills and outlines SHALL provide context below the existing interactive data overlays. District fills SHALL remain below population density; point markers and counts SHALL remain above polygon overlays. District boundaries SHALL remain legible with the other datasets enabled. These relationships SHALL hold independently of enable order and asynchronous response completion.

#### Scenario: Districts finish loading last
- **WHEN** bins, landfills and population are visible before district data arrives
- **THEN** districts render beneath the existing data overlays without covering markers or changing their behavior

#### Scenario: Districts finish loading first
- **WHEN** district data arrives before the other selected datasets
- **THEN** later population and point rendering retains the same layer ordering and district readability

#### Scenario: Enable every current layer
- **WHEN** all four layers are enabled together
- **THEN** district context, population shading, point markers and counts remain simultaneously usable
- **AND** none of the polygon rendering is passed through point clustering

