# Spec Delta

## Purpose

Provide independently selectable map datasets with consistent point clustering and feature interactions, while permitting later geographic layer types to join the same map.

## ADDED Requirements

### Requirement: Independent layer selection
The `Sluoksniai` section SHALL list registered datasets with labeled checkboxes showing dataset names without descriptive paragraphs. Checking a layer SHALL display it; unchecking SHALL hide it. Multiple layers SHALL be selectable simultaneously without disabling one another. Initially all checkboxes SHALL be unchecked, and only `Sąvartynai` SHALL be offered in this change.

#### Scenario: Enable the first layer
- **WHEN** an administrator checks `Sąvartynai`
- **THEN** its data loads and its points or clusters become visible

#### Scenario: Hide a visible layer
- **WHEN** an administrator unchecks a visible layer
- **THEN** its features and popup disappear while the basemap remains usable

#### Scenario: Select multiple registered datasets
- **WHEN** future independently registered datasets are selected together
- **THEN** all selected layers remain enabled and disabling one preserves the others
- **AND** the shipped panel contains no placeholder future layers

### Requirement: Lazy loading and session reuse
Opening the map SHALL NOT fetch unchecked layer datasets. Each layer SHALL load on first enable and reuse successful data during that page session. Repeated toggles SHALL share pending reads and SHALL NOT refetch cached data. A completed read for a disabled layer SHALL NOT make it visible.

#### Scenario: Open the map without a layer
- **WHEN** the analytics page first opens
- **THEN** the basemap loads without a landfill request

#### Scenario: Re-enable cached data
- **WHEN** a successfully loaded layer is disabled and enabled again during the page session
- **THEN** its cached features reappear without another data request

#### Scenario: Toggle during loading
- **WHEN** a layer is unchecked before its pending request finishes
- **THEN** successful data can be cached but its features remain hidden
- **AND** re-enabling during that request does not start a duplicate read

### Requirement: Independent loading and failure recovery
Each layer SHALL expose its own loading, empty and error state beside its controls, with retry for failed reads. Failure of one dataset SHALL leave the basemap and other active datasets usable. A successful empty response SHALL be distinguished from loading or failure.

#### Scenario: Retry a failed dataset
- **WHEN** a layer request fails and the administrator activates its retry control
- **THEN** only that dataset is requested again and the current map view is preserved

#### Scenario: Load an empty dataset
- **WHEN** an enabled layer returns no features
- **THEN** its panel entry identifies an empty dataset without reporting a failure

### Requirement: Stable map view across layer changes
Layer selection and loading completion SHALL preserve the current map center and zoom and SHALL NOT recreate the map. Intentional user navigation and cluster expansion SHALL remain able to change the view.

#### Scenario: Toggle after exploring
- **WHEN** an administrator pans and zooms and then changes layer visibility
- **THEN** the map retains that center and zoom without a basemap reload

### Requirement: Automatic point-layer clustering
Every registered point layer SHALL group nearby points into zoom-dependent clusters, display each cluster's point count and reveal individual points when sufficiently zoomed in. Zooming out SHALL regroup nearby points. Clusters SHALL count only points from their own dataset. New point datasets SHALL receive this behavior through the shared point-layer capability.

#### Scenario: Zoom through cluster levels
- **WHEN** an administrator zooms in on nearby points and then zooms out
- **THEN** clusters split into smaller clusters or individual points and nearby points regroup on zoom-out
- **AND** each displayed cluster count matches the number of represented points

#### Scenario: Keep dataset counts separate
- **WHEN** multiple point datasets are visible in the same area
- **THEN** each dataset's clusters count only its own points

### Requirement: Cluster expansion and individual feature interaction
Activating a cluster SHALL zoom toward the level at which its points separate, without opening an individual-feature popup. Activating an unclustered point SHALL expose that dataset's feature details. Newly registered point datasets SHALL inherit cluster expansion while supplying their own detail content.

#### Scenario: Expand a landfill cluster
- **WHEN** an administrator activates a cluster containing nearby landfills
- **THEN** the map moves toward that cluster and zooms to reveal smaller clusters or individual landfill markers
- **AND** no landfill-details popup is opened for the aggregate

#### Scenario: Inspect an individual point
- **WHEN** an administrator activates an unclustered point
- **THEN** the displayed details correspond to that feature and its dataset

### Requirement: Layer identity and extension contract
Each layer SHALL have a stable ID, display name, dataset meaning, render kind, color-meaning legend entries and independent visibility state. Extensions SHALL be able to register point or non-point renderers without replacing the map screen or treating polygons/grids as markers. Active IDs and their dataset definitions SHALL be available to later in-app consumers without implementing an analytics assistant.

#### Scenario: Add another point definition
- **WHEN** a future point dataset is registered with its loader, appearance and feature details
- **THEN** it appears in the common selector and uses the existing clustering and expansion behavior

#### Scenario: Add a non-point renderer
- **WHEN** a future polygon or grid renderer joins the layer contract
- **THEN** its visibility and loading use the common controls without point clustering being applied to its geometry
- **AND** no polygon/grid renderer or calculation is shipped in this change

#### Scenario: Identify displayed datasets
- **WHEN** later application code reads the active layer selection
- **THEN** it can resolve each active ID to its dataset meaning independently of localized labels

### Requirement: Extensible color legend
Each registered dataset SHALL define its color meanings. The screen SHALL display all registered color meanings in a labeled `Legenda` section after the layer checkboxes in the shared card underneath the map. Color swatches SHALL have accompanying text, and the legend SHALL support multiple entries per dataset without assuming point geometry. The initial landfill pins and clusters SHALL be green, matching the `Sąvartynai` legend entry.

#### Scenario: Identify landfill color
- **WHEN** the analytics screen opens
- **THEN** a green swatch labeled `Sąvartynai` appears under the map
- **AND** enabled landfill pins and clusters use that green color

#### Scenario: Extend color meanings
- **WHEN** a future dataset supplies multiple color categories or a non-point renderer
- **THEN** its color meanings appear through the common legend
- **AND** a point definition can color individual features by recorded properties without replacing the map page
- **AND** this change adds no bin, district or other future dataset
