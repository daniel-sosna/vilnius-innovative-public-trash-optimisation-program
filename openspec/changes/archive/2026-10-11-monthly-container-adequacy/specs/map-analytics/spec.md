# Spec Delta

## ADDED Requirements

### Requirement: Saved adequacy analysis catalog
`GET /map-analytics/adequacy-analyses` SHALL list validated imported analyses in descending period order with opaque ID, month, period bounds, completion status, schema/method versions, revision and fill provenance. The initial catalog SHALL list completed-month artifacts only. An empty imported-analysis table SHALL return an empty catalog; database read errors SHALL report a failed read.

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

### Requirement: Read saved adequacy GeoJSON
`GET /map-analytics/adequacy-analyses/{analysis_id}` SHALL return the selected imported GeoJSON collection with its analysis metadata and feature properties. Retrieval SHALL be constrained to imported catalog identities. Unknown IDs SHALL return 404; database failures SHALL return a failed read. Reads SHALL never regenerate analysis or require source CSV access.

#### Scenario: Source data unavailable after generation
- **WHEN** a result is imported but its GeoJSON file and original registry/fill CSVs are unavailable
- **THEN** catalog discovery and result retrieval still succeed without rebuilding data

#### Scenario: Invalid analysis identifier
- **WHEN** a request contains an unknown ID or attempts to address a filesystem path
- **THEN** it cannot access filesystem paths or unrelated database records

### Requirement: Existing-card analysis selection
The analytics screen SHALL add `Konteinerių pakankamumas` and its month/type controls to the existing `Sluoksniai` / `Legenda` card below the map. Available months SHALL come from the catalog and use Lithuanian labels with years. One month and one supported waste type SHALL be active at a time. Controls SHALL follow existing styling, accessibility and 320-pixel responsiveness.

#### Scenario: Select an available month
- **WHEN** an administrator first enables analysis with saved completed months available
- **THEN** the latest completed month and mixed waste are initially selected
- **AND** the month control offers only catalog entries and the color legend remains in the shared card

#### Scenario: No analyses or failed catalog
- **WHEN** the analysis catalog is empty or fails
- **THEN** the controls distinguish `Duomenų nėra.` from `Nepavyko įkelti sluoksnio.` with `Bandyti dar kartą` for failure
- **AND** the basemap and other layers remain usable

### Requirement: Explain residential adequacy details
Analysis popups SHALL use short Lithuanian titles, seven metric rows (month, type, residents, point bins, pressure/reference, distance, level-4 counts/frequency) and one concise conclusion. Unknowns SHALL display `N/A`; point metrics SHALL be labeled. Diagnostics and provenance SHALL remain in GeoJSON. Popups SHALL omit synthetic-data notices and lengthy methodology.

#### Scenario: Inspect priority area
- **WHEN** an administrator opens a priority shortage candidate
- **THEN** the compact popup shows pressure/reference and level-4 source counts
- **AND** its conclusion recommends checking capacity or frequency without claiming measured causality

#### Scenario: Inspect sparse evidence
- **WHEN** an area has elevated pressure but insufficient fill assessments
- **THEN** the popup retains the pressure explanation and identifies insufficient fill evidence
- **AND** it does not display an invented zero level-4 frequency

### Requirement: Refresh saved analysis availability
The analysis controls SHALL provide a catalog refresh using existing button styling. Refresh SHALL discover newly imported months and revisions without generating data or recreating the map. The selected month SHALL remain selected if available; if its revision changes, its cached dataset SHALL be invalidated. Initial monthly delivery SHALL NOT add a selected-today control.

#### Scenario: Add a new month while the screen is open
- **WHEN** an operator imports another completed month and the administrator refreshes the analysis list
- **THEN** the new month becomes selectable while the existing selected month and camera are preserved

#### Scenario: Explicit regeneration of selected month
- **WHEN** catalog refresh reports a new revision for the selected month
- **THEN** the next displayed analysis uses that revision rather than stale session data
- **AND** completed-month regeneration is not triggered by the refresh itself
