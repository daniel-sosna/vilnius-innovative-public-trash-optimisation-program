# Spec Delta

## MODIFIED Requirements

### Requirement: Independent analysis selection
The analysis layer SHALL start unchecked. Its month and waste-type selection SHALL be independent of the existing bin-category controls and survive hiding/re-enabling within a page session. Changing type SHALL filter the loaded monthly file without another result request; changing month SHALL fetch or reuse that month's eligible saved result without affecting other layer selections. September SHALL use the shared project date as its inclusive cutoff, with no independent day selector.

#### Scenario: Choose glass analysis with mixed bins visible
- **WHEN** an administrator selects glass analysis while the bin layer shows mixed waste
- **THEN** the analysis displays glass metrics and the bin layer preserves its existing category selection

#### Scenario: Hide and restore analysis
- **WHEN** analysis is disabled and re-enabled after choosing a month/type
- **THEN** that month/type is restored using valid cached data
- **AND** disabling closes only the analysis-owned popup

#### Scenario: Move the September cutoff
- **WHEN** September risk analysis is active and the calendar changes from September 18 to September 7
- **THEN** the layer switches to September 1–7, preserves waste type and map state, and hides September 1–18 immediately

#### Scenario: No exact prepared cutoff
- **WHEN** September is selected but the calendar date has no imported matching result
- **THEN** the layer shows missing-data feedback without rendering an earlier or later September result


### Requirement: Analysis loading follows selected artifact identity
Analysis SHALL share pending reads and cache successful results by artifact ID and revision. Switching month, September cutoff or revision SHALL hide stale geometry and close the analysis popup while preserving camera, map instance and unrelated filters. Late responses SHALL not display a superseded selection or revive a disabled layer. Retry SHALL affect only the selected failed analysis read.

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

#### Scenario: Change date during loading
- **WHEN** September 18 is requested and the calendar changes to September 7 before completion
- **THEN** the old response cannot render or reopen its popup
- **AND** returning to September 18 can reuse its valid cached artifact without another result request

