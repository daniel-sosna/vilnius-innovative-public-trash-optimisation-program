# Spec Delta

## MODIFIED Requirements

### Requirement: Collection browsing preserves operational data and import
Collection GET requests SHALL remain read-only and preserve stored operational data and import progress. Explicit management actions SHALL create/delete records only under the collection-site-management contract. The required manual-management migration SHALL preserve existing data and PostgreSQL storage. Browsing, management and application startup SHALL NOT invoke import or reset tables; an independently invoked importer SHALL remain independent.

#### Scenario: Browse during import
- **WHEN** an administrator requests sites, statistics, bins or history while import is progressing
- **THEN** the feature reads committed records without modifying data, schema or import progress
- **AND** the importer continues independently

#### Scenario: Activate after completed import
- **WHEN** the completed one-time import is followed by activation of collection management through the real Compose setup
- **THEN** the required migration and rebuilt application preserve existing records and database storage
- **AND** no automatic import or table reset occurs

#### Scenario: Start separate verification servers
- **WHEN** separate frontend/backend servers are started for browsing verification
- **THEN** verification GET requests do not mutate the registry or import checkpoints
- **AND** startup performs no import or storage reset

#### Scenario: Browse after a manual mutation
- **WHEN** an administrator explicitly creates or deletes collection records and then requests the list, details or statistics
- **THEN** the reads reflect committed records without themselves creating, deleting or editing data

### Requirement: Informational site location
Site details SHALL show a marker at the stored Site longitude and latitude, with visible street names and surrounding streets. The map SHALL allow panning and zooming by drag, wheel, touch, keyboard and labeled zoom-in/zoom-out controls. Its style SHALL use configurable `VITE_MAP_STYLE_URL`, initially `https://tiles.openfreemap.org/styles/liberty`. Documentation SHALL distinguish imported derived coordinates from manual selected coordinates; viewing SHALL NOT edit either location.

#### Scenario: View the site map
- **WHEN** a site with valid coordinates is opened
- **THEN** the map centers its marker on the stored Site coordinate without swapping latitude and longitude
- **AND** drag can change the map center and wheel, touch, keyboard and the zoom buttons can change the view

#### Scenario: Configure another map style
- **WHEN** the frontend is started or built with a different valid `VITE_MAP_STYLE_URL`
- **THEN** it loads that configured style without requiring map-component changes

#### Scenario: Handle unavailable map resources
- **WHEN** map configuration, coordinates or external map resources are unavailable
- **THEN** the map area shows a clear Lithuanian unavailable/error state, using `N/A` for missing coordinate values
- **AND** site statistics and bins remain usable

#### Scenario: Keep detail locations informational
- **WHEN** an administrator pans, zooms or clicks an existing Site's detail map
- **THEN** the displayed Site marker and stored Site coordinates remain unchanged
- **AND** location selection is available only in the new-Site modal

### Requirement: Explicit NULL and numeric fill presentation
Every displayed database NULL SHALL appear as `N/A` in lists, metrics, site details, dialog headers and history. Editable form fields SHALL use normal empty inputs instead. Values 0 and false SHALL remain meaningful values. History fill level SHALL display its stored integer 0–3 directly, without category labels, inferred percentages or predictions. API nulls SHALL remain nulls rather than becoming display strings.

#### Scenario: Render nullable bin and history values
- **WHEN** inventory number, capacity, failure reason or fill level is NULL
- **THEN** its displayed field shows `N/A`, never raw null, undefined or an empty NULL placeholder

#### Scenario: Display each numeric fill observation
- **WHEN** attempts have fill levels 0, 1, 2, 3 and NULL
- **THEN** the corresponding displayed values are 0, 1, 2, 3 and `N/A`
- **AND** an unsuccessful boolean status displays its Lithuanian unsuccessful status rather than `N/A`

#### Scenario: Enter an optional missing postal code
- **WHEN** an administrator leaves the new-Site postal-code field empty
- **THEN** the input remains empty, creation stores NULL, and subsequent Site detail display shows `N/A`

## ADDED Requirements

### Requirement: Compact Site list addresses
Site list rows SHALL display only the street name and house number from the registered display address, omitting appended sub-district and postal code. Existing unknown-address fallbacks SHALL remain readable. Full stored addresses, search matching and detail/API address values SHALL remain intact.

#### Scenario: Browse a manually created Site
- **WHEN** a Site has address `Didlaukio g. 53A, Verkių sen., 08303`
- **THEN** its list row shows `Didlaukio g. 53A`
- **AND** its details and deletion confirmation retain the full address
