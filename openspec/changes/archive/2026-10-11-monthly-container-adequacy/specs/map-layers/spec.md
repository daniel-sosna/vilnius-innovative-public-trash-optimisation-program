# Spec Delta

## ADDED Requirements

### Requirement: Adequacy polygon layer and legend
Residential adequacy SHALL render the selected month's population-area geometry for one waste type as translucent category polygons, preserving holes and stable feature identities. The shared legend SHALL distinguish priority shortage, potential shortage, elevated level-4 evidence without elevated pressure, ordinary assessment, insufficient evidence and unavailable assessment. Category colors SHALL be stable across months.

#### Scenario: Compare two months
- **WHEN** the administrator switches between saved months using the same reference snapshot
- **THEN** geometry identities and category color meanings remain stable
- **AND** the renderer does not recalculate thresholds for the visible viewport

#### Scenario: Unknown population remainder
- **WHEN** an analysis file includes a polygon with unknown population
- **THEN** it has no filled analysis area and cannot capture clicks
- **AND** unavailable assessment remains explained by the legend

### Requirement: Independent analysis selection
The analysis layer SHALL start unchecked. Its month and waste-type selection SHALL be independent of the existing bin-category controls and survive hiding/re-enabling within a page session. Changing type SHALL filter the loaded monthly file without another result request; changing month SHALL fetch or reuse that month's saved result without affecting other layer selections.

#### Scenario: Choose glass analysis with mixed bins visible
- **WHEN** an administrator selects glass analysis while the bin layer shows mixed waste
- **THEN** the analysis displays glass metrics and the bin layer preserves its existing category selection

#### Scenario: Hide and restore analysis
- **WHEN** analysis is disabled and re-enabled after choosing a month/type
- **THEN** that month/type is restored using valid cached data
- **AND** disabling closes only the analysis-owned popup

### Requirement: Analysis loading follows selected artifact identity
Analysis SHALL share pending reads and cache successful results by artifact ID and revision. Switching month or revision SHALL hide stale geometry and close the analysis popup while preserving camera, map instance and unrelated filters. Late responses SHALL not display a superseded selection or revive a disabled layer. Retry SHALL affect only the selected failed analysis read.

#### Scenario: Switch months during loading
- **WHEN** July is requested and August is selected before July completes
- **THEN** July's response cannot appear as August's analysis
- **AND** only the currently selected ready artifact is rendered

#### Scenario: Disable during loading
- **WHEN** the layer is disabled before the selected result arrives
- **THEN** the response may be cached but does not show polygons or reopen a popup

#### Scenario: Independent loading failure
- **WHEN** the selected result cannot be read
- **THEN** analysis displays the existing Lithuanian error and retry controls
- **AND** no previous month's geometry is shown under the failed month's label

### Requirement: Analysis ordering and interaction priority
Analysis fills SHALL appear above population shading and below point markers, point counts and service-zone outlines/names, independently of load order. Point interactions SHALL take precedence. Away from points, the topmost interactive polygon SHALL own the click, so an analysis popup is not immediately replaced by a population popup. Context-only layers SHALL remain non-interactive.

#### Scenario: All existing layers and analysis enabled
- **WHEN** analysis, bins, population, districts, service zones and landfills are enabled
- **THEN** analysis categories, point markers and service-zone boundaries remain usable
- **AND** no analysis polygon participates in point clustering

#### Scenario: Click analysis over population
- **WHEN** an analysis polygon is activated above population shading away from markers
- **THEN** only the analysis popup opens
- **AND** hiding analysis restores existing population interaction

#### Scenario: Click bin above analysis
- **WHEN** a bin marker or count group is activated above analysis
- **THEN** only its existing bin interaction occurs

### Requirement: Responsive analysis controls preserve map state
Month/type controls and the analysis legend SHALL remain within the existing shared card, keyboard-operable and usable at 320 pixels without page-wide horizontal scrolling. Selecting, refreshing or hiding analysis SHALL preserve map center, zoom, bearing, pitch and unrelated layer state.

#### Scenario: Change month after navigating
- **WHEN** an administrator pans and zooms, then changes the analysis month
- **THEN** the same map instance and camera remain active while the selected analysis changes

#### Scenario: Narrow-screen selection
- **WHEN** analysis controls are opened at 320-pixel width
- **THEN** labels wrap or scroll within the existing layout and the map and color legend remain reachable
