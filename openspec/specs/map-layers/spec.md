# map-layers Specification

## Purpose

Provide independently selectable map datasets with consistent point clustering and feature interactions, while permitting later geographic layer types to join the same map.

## Requirements

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
Every registered point layer SHALL group nearby points into zoom-dependent clusters, display each cluster's point count and reveal individual points when sufficiently zoomed in. Zooming out SHALL regroup nearby points. Clusters SHALL count only points from their own dataset. New point datasets SHALL receive this behavior through the shared point-layer capability. Bins still overlapping at high zoom SHALL remain grouped, including those at identical coordinates. Bin grouping SHALL use larger aggregates at lower zoom and merge colliding markers until rendered bin circles, including their strokes, do not overlap.

#### Scenario: Zoom through cluster levels
- **WHEN** an administrator zooms in on nearby points and then zooms out
- **THEN** clusters split into smaller clusters or individual points and nearby points regroup on zoom-out
- **AND** each displayed cluster count matches the number of represented points

#### Scenario: Keep dataset counts separate
- **WHEN** multiple point datasets are visible in the same area
- **THEN** each dataset's clusters count only its own points

#### Scenario: Retain identical-coordinate bins at high zoom
- **WHEN** two or more matching bins share identical coordinates and the administrator reaches high zoom or the map's maximum zoom
- **THEN** one count marker represents them instead of inaccessible overlapping individual markers
- **AND** its count includes each represented bin exactly once

#### Scenario: Retain near-coordinate bins at high zoom
- **WHEN** two or more matching bins at very similar coordinates remain within the marker grouping tolerance at high zoom
- **THEN** a count marker represents the group
- **AND** zooming sufficiently to separate their markers reveals individual bins when separation is possible

### Requirement: Cluster expansion and individual feature interaction
Activating an ordinary cluster SHALL zoom toward the level at which its points separate, without opening an individual-feature popup. Activating an unclustered point SHALL expose that dataset's feature details. Newly registered point datasets SHALL inherit cluster expansion while supplying their own detail content. Activating a high-zoom bin overlap group SHALL instead open its selectable bin list without changing the map view.

#### Scenario: Expand a landfill cluster
- **WHEN** an administrator activates a cluster containing nearby landfills
- **THEN** the map moves toward that cluster and zooms to reveal smaller clusters or individual landfill markers
- **AND** no landfill-details popup is opened for the aggregate

#### Scenario: Inspect an individual point
- **WHEN** an administrator activates an unclustered point
- **THEN** the displayed details correspond to that feature and its dataset

#### Scenario: Expand an ordinary bin cluster
- **WHEN** an administrator activates a bin cluster below the high-zoom overlap interaction range
- **THEN** the map zooms toward that cluster's expansion level
- **AND** no bin list or individual-bin popup opens for that activation

#### Scenario: Open a high-zoom overlap group
- **WHEN** an administrator activates a high-zoom bin count marker
- **THEN** the group opens its selectable bin list at the current map center and zoom
- **AND** further zoom is not required to inspect every represented bin

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

### Requirement: Bin waste-type modal controls
`Konteineriai` SHALL have a small arrow button beside its main checkbox that opens waste-type controls in a modal. Categories SHALL be independently selectable and selected by default. Opening or closing the modal SHALL NOT change selections or layer visibility. The dialog SHALL support keyboard focus trapping, Escape dismissal and focus restoration to its trigger.

#### Scenario: Enable all known types
- **WHEN** the bin layer is first enabled and its waste-type modal is opened
- **THEN** `Popieriaus ir plastiko atliekos`, `Stiklo atliekos` and `Mišrios komunalinės atliekos` are selected and all loaded bins of those categories are eligible for display

#### Scenario: Use the modal independently
- **WHEN** the administrator closes or reopens the modal
- **THEN** its category selections and the main layer selection remain unchanged
- **AND** its arrow control is separate from the main checkbox and usable by keyboard

#### Scenario: Use compact controls on a narrow screen
- **WHEN** the analytics page is viewed at 320 pixels wide with the modal open
- **THEN** the modal controls remain readable and operable with internal scrolling when needed
- **AND** the card stays below the map, with the legend reachable

### Requirement: Session-preserved bin category selection
Bin category selections SHALL survive disabling and re-enabling `Konteineriai` during the page session, including when every category is deselected. A new page session SHALL initialize all categories as selected. Hiding the layer SHALL NOT reset category choices or refetch successfully cached data.

#### Scenario: Restore a subset after toggling
- **WHEN** only glass is selected and the administrator disables and re-enables the bin layer
- **THEN** only glass remains selected and cached matching bins reappear without another dataset request

#### Scenario: Restore an empty category selection
- **WHEN** every category is deselected and the administrator disables and re-enables the layer
- **THEN** the layer is enabled with all categories still deselected and no bin points or count markers displayed

#### Scenario: Reset in a new page session
- **WHEN** the analytics page is reopened or refreshed as a new session
- **THEN** the layer starts unchecked and all categories are selected when first enabled

### Requirement: Waste filters update bin points and groups
Changing a bin waste-category selection SHALL update visible individual bins, clusters and high-zoom overlap groups to contain only matching bins. All-deselected categories SHALL leave `Konteineriai` enabled with no bin points or count markers. Filter changes SHALL preserve the map view, basemap and other layer visibility, without another dataset request. Zooming and visibility toggles SHALL NOT repeat category transformations.

#### Scenario: Exclude one category from a mixed group
- **WHEN** the administrator deselects paper/plastic in a group containing different waste types
- **THEN** paper/plastic bins disappear and every remaining cluster or overlap count excludes them
- **AND** opening a remaining overlap group exposes only its currently represented bins

#### Scenario: Reduce an overlap group to one bin
- **WHEN** a filter change leaves one matching bin in a high-zoom overlap group
- **THEN** that bin appears as an individual marker with its waste-category color
- **AND** its marker opens that bin's details directly

#### Scenario: Deselect all categories
- **WHEN** the administrator deselects every category
- **THEN** the main layer checkbox remains checked but no bin markers or count labels remain
- **AND** the controls distinguish an empty selection from an empty source dataset and from a failed read

#### Scenario: Preserve camera and requests during filtering
- **WHEN** the administrator changes categories after panning and zooming with both datasets enabled
- **THEN** the map center and zoom and the landfill layer remain unchanged
- **AND** no dataset request or basemap reload occurs

### Requirement: Bin waste-category colors and fallback
Individual bin markers SHALL be blue for `Paper/plastic waste`, green for `Glass waste` and brown for `Mixed municipal waste`. Other strings SHALL use gray and the category label `Kitos atliekų rūšys`. A single category mapping SHALL keep bin marker colors, modal labels and legend meanings consistent. Bin count markers SHALL use a uniform neutral color rather than imply one waste type.

#### Scenario: Render the observed source categories
- **WHEN** individual bins with the three known stored waste types are visible
- **THEN** each marker uses its corresponding blue, green or brown category color and Lithuanian presentation

#### Scenario: Gracefully display an unexpected type
- **WHEN** loaded bin data includes one or more waste-type strings outside the three known values
- **THEN** those bins are gray and grouped under one initially selected `Kitos atliekų rūšys` checkbox
- **AND** toggling that checkbox filters all unexpected types together without affecting known categories or failing the layer
- **AND** when no unexpected values exist, the fallback checkbox is omitted

#### Scenario: Render a mixed count marker
- **WHEN** a cluster or high-zoom group contains bins of different waste types
- **THEN** its marker uses the same neutral count-marker color as other bin groups and displays the represented count

### Requirement: Collision-free bin aggregation
Rendered bin circles SHALL remain disjoint at integer and fractional zooms. Overlapping bin groups SHALL merge into one marker with the exact combined count and complete member identity; merged centers and changed marker sizes SHALL be checked again until no collision remains. Each dataset retains its own counts and interaction.

#### Scenario: Merge a dense low-zoom view
- **WHEN** bin count markers would overlap at a low zoom
- **THEN** colliding groups merge into larger groups whose circles and strokes do not overlap
- **AND** each represented bin contributes once to the exact count

#### Scenario: Recheck a moved aggregate
- **WHEN** merging groups moves an aggregate center or increases its radius into another marker
- **THEN** the new collision is also merged before displaying the result

#### Scenario: Keep camera updates current
- **WHEN** zoom, pan, bearing, pitch or viewport size changes
- **THEN** current screen geometry is used for bin grouping without another dataset read
- **AND** obsolete layouts and group reads cannot restore overlapping markers or stale membership

#### Scenario: Keep selected bins visible during navigation
- **WHEN** an administrator pans, zooms, rotates or resizes a map showing bins
- **THEN** the bin layer remains visible while its clusters update
- **AND** camera-driven regrouping does not hide bin circles or count labels while waiting for worker or tile readiness

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
