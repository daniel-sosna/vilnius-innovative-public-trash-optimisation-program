# Spec Delta

## MODIFIED Requirements

### Requirement: Independent layer selection
The `Sluoksniai` section SHALL list all registered datasets with labeled checkboxes showing dataset names without descriptive paragraphs. Checking a layer SHALL display it; unchecking SHALL hide it. Multiple layers SHALL be selectable simultaneously without disabling one another. Dataset controls SHALL be vertically arranged in the shared sidebar, with subordinate filters under their dataset. Initially all checkboxes SHALL be unchecked. `Sąvartynai`, `Konteineriai`, `Gyventojų tankumas`, `Seniūnijos` and `Aptarnavimo zonos` SHALL be offered together.

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
- **WHEN** the dataset controls appear in the layers sidebar
- **THEN** checkboxes and labels form a scannable vertical list, with bin waste filters indented beneath their parent

#### Scenario: Select the district overlay with every current dataset
- **WHEN** all five shipped layer checkboxes are selected
- **THEN** all five datasets remain enabled and visible together
- **AND** district visibility changes preserve other selections and bin category filters

#### Scenario: Preserve the existing screen
- **WHEN** the new district option is displayed
- **THEN** the full-screen map, shared overlay sidebar and existing legends remain available
- **AND** the added control remains reachable at 320-pixel widths


#### Scenario: Enable all current datasets
- **WHEN** all five datasets are selected
- **THEN** district boundaries, service zones, population polygons, landfill markers and matching bin markers or groups remain visible together
- **AND** toggling zones preserves the other selections and bin filters

### Requirement: Extensible color legend
Each registered dataset SHALL define its color meanings where a legend is applicable; the district and service-zone context overlays SHALL provide no legend entries. The screen SHALL display legend entries only for selected datasets in a labeled `Legenda` section after the layer checkboxes in the layers mode of the shared sidebar, vertically arranged. When no layer is selected, the section SHALL display `Nepasirinktas sluoksnis`. Color swatches SHALL have accompanying text, and the legend SHALL support multiple entries per dataset without assuming point geometry. Landfill pins and clusters SHALL be black, matching the `Sąvartynai` legend entry. Bin entries SHALL identify category and group colors.

#### Scenario: Identify landfill color
- **WHEN** the landfill layer is selected
- **THEN** a black swatch labeled `Sąvartynai` appears in the shared sidebar legend
- **AND** enabled landfill pins and clusters use that black color

#### Scenario: Extend color meanings
- **WHEN** a selected dataset supplies multiple color categories or a non-point renderer with legend entries
- **THEN** its color meanings appear through the common legend
- **AND** a point definition can color individual features by recorded properties without replacing the map page
- **AND** the bin categories are included without adding district or other future datasets

#### Scenario: Distinguish bin categories from counts
- **WHEN** the administrator selects bins and views the legend
- **THEN** labeled blue, green and brown swatches identify the known bin waste categories
- **AND** gray identifies `Kitos atliekų rūšys` and a separately labeled neutral swatch identifies `Konteinerių grupė`

#### Scenario: Preserve legends when adding districts
- **WHEN** Seniūnijos is registered or toggled
- **THEN** no district swatches or new analytics legend section are added
- **AND** legend entries for selected landfill, bin and population layers remain available


#### Scenario: Preserve the legend when zones are registered
- **WHEN** the page opens or service zones are toggled
- **THEN** legend entries for selected landfill, bin and population layers remain unchanged
- **AND** no service-zone legend, metric scale or separate zone-specific panel is added

### Requirement: Bin waste-type modal controls
`Konteineriai` SHALL expose independently selectable waste categories beneath its main checkbox in the shared layers sidebar. Categories SHALL be selected by default. Closing, reopening or switching sidebar modes SHALL NOT change category selections or layer visibility. Filters SHALL be operable by keyboard and touch without a separate category modal.

#### Scenario: Enable all known types
- **WHEN** the bin layer is first enabled and its waste-type sidebar controls are visible
- **THEN** `Popieriaus ir plastiko atliekos`, `Stiklo atliekos` and `Mišrios komunalinės atliekos` are selected and all loaded bins of those categories are eligible for display

#### Scenario: Use the modal independently
- **WHEN** the administrator closes, reopens or switches the sidebar
- **THEN** its category selections and the main layer selection remain unchanged
- **AND** its category controls are subordinate to the main checkbox and usable by keyboard

#### Scenario: Use compact controls on a narrow screen
- **WHEN** the analytics page is viewed at 320 pixels wide with the layers sidebar open
- **THEN** the sidebar category controls remain readable and operable with internal scrolling when needed
- **AND** the map keeps its full available size behind the panel, with the legend reachable through internal scrolling

### Requirement: Bin waste-category colors and fallback
Individual bin markers SHALL be blue for `Paper/plastic waste`, green for `Glass waste` and brown for `Mixed municipal waste`. Other strings SHALL use gray and the category label `Kitos atliekų rūšys`. A single category mapping SHALL keep bin marker colors, sidebar labels and legend meanings consistent. Bin count markers SHALL use a uniform neutral color rather than imply one waste type.

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

### Requirement: Population density legend
The shared `Legenda` SHALL include five labelled purple swatches identifying population density bands in `gyv./ha`, plus a transparent missing-data entry. Colours SHALL match displayed polygons and coexist with existing dataset entries, only while population is selected.

#### Scenario: Read the density scale
- **WHEN** an administrator selects population and views the legend
- **THEN** entries identify `Gyventojų tankumas`, all five density bands and `gyv./ha`
- **AND** `Duomenų nėra (skaidru)` identifies transparent missing data alongside other dataset legends

#### Scenario: Narrow screen
- **WHEN** the page is viewed at 320 pixels wide
- **THEN** legend labels wrap inside the shared sidebar without horizontal page scrolling

#### Scenario: Hide unselected legend entries
- **WHEN** an administrator unchecks a layer
- **THEN** that layer's legend items disappear while selected layers' items remain

#### Scenario: No layers selected
- **WHEN** no layer is selected
- **THEN** the legend displays `Nepasirinktas sluoksnis` without swatches
