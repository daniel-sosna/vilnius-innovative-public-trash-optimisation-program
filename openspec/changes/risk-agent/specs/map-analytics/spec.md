# Spec Delta

## MODIFIED Requirements

### Requirement: Saved adequacy analysis catalog
`GET /map-analytics/adequacy-analyses` SHALL list validated imported analyses in descending period order with opaque ID, month, period bounds, completion status, schema/method versions, revision and fill provenance. The catalog SHALL accept an optional September 2026 `project_date` and list completed months ending no later than that date plus the exact prepared September cutoff. Without a date it SHALL list completed-month artifacts only; invalid dates SHALL return HTTP 422. An empty imported-analysis table SHALL return an empty catalog; database read errors SHALL report a failed read.

#### Scenario: Newly generated month
- **WHEN** a valid complete monthly GeoJSON is explicitly imported into the database
- **THEN** the next catalog request includes it without a frontend rebuild

#### Scenario: No saved results
- **WHEN** no analyses have been imported
- **THEN** the catalog succeeds with an empty analysis list

#### Scenario: Invalid published result
- **WHEN** the database is unavailable
- **THEN** discovery reports a failed read rather than an empty-success substitute
- **AND** generated files that have not been imported are not considered published results

#### Scenario: Discover dated September data
- **WHEN** the catalog is requested for September 18
- **THEN** September 1–18 and eligible earlier completed months are listed
- **AND** September 19–30 and full September are excluded


### Requirement: Shared-sidebar analysis selection
The analytics screen SHALL add `Konteinerių pakankamumas` and its month/type controls to the existing `Sluoksniai` / `Legenda` overlay sidebar, with month/type controls beneath the analysis checkbox. Available months SHALL come from the date-filtered catalog and use Lithuanian labels with years; September SHALL resolve only to the exact shared-calendar cutoff. One month and one supported waste type SHALL be active at a time. Controls SHALL follow existing styling, accessibility and 320-pixel responsiveness.

#### Scenario: Select an available month
- **WHEN** an administrator first enables analysis with saved completed months available
- **THEN** September at the exact selected cutoff and mixed waste are initially selected when available; otherwise the selected September period reports missing data without substituting a different period
- **AND** the month control offers only catalog entries and the color legend remains in the shared sidebar

#### Scenario: No analyses or failed catalog
- **WHEN** the analysis catalog is empty or fails
- **THEN** the controls distinguish `Duomenų nėra.` from `Nepavyko įkelti sluoksnio.` with `Bandyti dar kartą` for failure
- **AND** the basemap and other layers remain usable

#### Scenario: Preserve earlier-month choice
- **WHEN** August is selected and the shared date changes within September
- **THEN** August remains selected, and choosing September displays the exact current cutoff


### Requirement: Explain residential adequacy details
Analysis popups SHALL use short Lithuanian titles, seven metric rows (period, type, residents, point bins, pressure/reference, distance, level-4 counts/frequency) and one concise conclusion. Unknowns SHALL display `N/A`; point metrics SHALL be labeled. Diagnostics and provenance SHALL remain in GeoJSON. Popups SHALL omit synthetic-data notices and lengthy methodology.

#### Scenario: Inspect priority area
- **WHEN** an administrator opens a priority shortage candidate
- **THEN** the compact popup shows pressure/reference and level-4 source counts
- **AND** its conclusion recommends checking capacity or frequency without claiming measured causality

#### Scenario: Inspect sparse evidence
- **WHEN** an area has elevated pressure but insufficient fill assessments
- **THEN** the popup retains the pressure explanation and identifies insufficient fill evidence
- **AND** it does not display an invented zero level-4 frequency

#### Scenario: Inspect a partial period
- **WHEN** September 18 risk data is displayed
- **THEN** the controls and popup identify September 1–18 as a partial-month period
- **AND** September 30 is identified as a completed month


### Requirement: Refresh saved analysis availability
The analysis controls SHALL omit a manual catalog-refresh button. Enabling the layer, enabled calendar changes and catalog-error retry SHALL refresh discovery without generating data or recreating the map. The selected month SHALL remain selected if available; if its revision changes, its cached dataset SHALL be invalidated. The shared navbar calendar SHALL remain the only day selector; refresh SHALL retain the exact cutoff constraint.

#### Scenario: Add a new month while the screen is open
- **WHEN** an operator imports another completed month and the administrator disables and re-enables the analysis layer
- **THEN** the new month becomes selectable while the existing selected month and camera are preserved

#### Scenario: Explicit regeneration of selected month
- **WHEN** catalog refresh reports a new revision for the selected month
- **THEN** the next displayed analysis uses that revision rather than stale session data
- **AND** completed-month regeneration is not triggered by the refresh itself

### Requirement: Shared project date access
Map Analytics SHALL observe the application-wide project date without initializing or persisting its own independent selection. Date access SHALL preserve filtering and map camera. Date selection SHALL permit reads of the date-filtered saved adequacy catalog and result, invalidate agent results and SHALL NOT automatically start agent analysis or generation.

#### Scenario: Share the Demo selection
- **WHEN** the administrator selects September 14 in Demo and opens Map Analytics
- **THEN** Map Analytics observes `2026-09-14` through the shared date state and the navbar shows the same selection

#### Scenario: Change date in Map Analytics
- **WHEN** the administrator changes the navbar date while viewing Map Analytics
- **THEN** the shared date updates without resetting layer selections, moving the map camera or automatically starting agent analysis
- **AND** Demo observes that same date when subsequently opened
