# Spec Delta

## ADDED Requirements

### Requirement: Read-only population map response
`GET /map-analytics/population-cells` SHALL return an unpaginated GeoJSON FeatureCollection of stored population polygons in ascending ID order. Each feature SHALL use the polygon ID, Polygon geometry in longitude/latitude with all rings, and only `density_per_ha`, `suppressed`, `area_ha` and `residents` properties. Numeric values SHALL be JSON numbers and suppression SHALL be a boolean.

#### Scenario: Read the stored grid
- **WHEN** the population map response is requested
- **THEN** each stored polygon appears exactly once with its ID, outer ring and holes
- **AND** merged polygons retain their geometry and area without subdivision
- **AND** no bin allocation, bounding-box fields, collection records or unrelated metadata is returned

#### Scenario: Empty population table
- **WHEN** no population polygons are stored
- **THEN** the response succeeds with an empty features array

### Requirement: Preserve population density uncertainty
The response SHALL retain numeric density as its stored value. Suppressed density SHALL have `density_per_ha: null`, `suppressed: true` and the stored estimated `residents`. Missing density SHALL have `density_per_ha: null`, `suppressed: false` and `residents: null`, rather than exposing a placeholder zero as a known population.

#### Scenario: Numeric density on a merged polygon
- **WHEN** a polygon stores density 14, area 3 hectares and estimated residents 42
- **THEN** its response preserves those numbers and suppression false

#### Scenario: Suppressed density
- **WHEN** a polygon represents `<11` with area 1 hectare and stored estimated residents 5
- **THEN** its response contains null density, suppression true, area 1 and residents 5

#### Scenario: Missing density
- **WHEN** a polygon has missing density, suppression false and stored residents 0
- **THEN** its response contains null density and null residents while retaining geometry and area
- **AND** its database values remain unchanged

### Requirement: Population reads do not rebuild data
Population map reads SHALL use the existing read-only collection snapshot, preserve stored data and require no source-file access or rebuild. Database failures SHALL follow the existing collection-read error contract rather than being reported as successful empty datasets.

#### Scenario: Read without the source file
- **WHEN** stored polygons exist and their source file is unavailable
- **THEN** reads remain available and neither population table changes

#### Scenario: Database unavailable
- **WHEN** the population dataset cannot be read
- **THEN** the endpoint reports a failed read rather than a successful empty response

### Requirement: Lithuanian population polygon details
Activating a displayed population polygon SHALL open a lightweight popup headed `Gyventojų tankumas`, with `Tankumas (gyv./ha)`, `Plotas (ha)` and `Apytikslis gyventojų skaičius`. Numeric density SHALL display its recorded value; suppressed density SHALL display `<11`. Area and estimated residents SHALL use Lithuanian number formatting, rounded to at most two and one decimal places respectively.

#### Scenario: Inspect numeric-density data
- **WHEN** an administrator activates a polygon with density 14, area 3 and estimated residents 42
- **THEN** the popup shows density 14, area 3 hectares and approximately 42 residents as distinct quantities

#### Scenario: Inspect merged geometry
- **WHEN** an administrator activates a merged polygon
- **THEN** its details use the full polygon's stored area and estimated residents, without assuming a 1-hectare square

### Requirement: Explain suppressed resident estimates
A suppressed polygon's popup SHALL distinguish the source bound `<11` from the assumption used for its estimated resident total. For positive area it SHALL display the applied estimate density obtained from stored residents divided by area. For zero area it SHALL explain the estimate without dividing by zero or inventing an applied density.

#### Scenario: Default assumption
- **WHEN** a suppressed polygon stores area 2 and estimated residents 10
- **THEN** the density row shows `<11` and an explanation identifies the estimate assumption as 5 residents per hectare

#### Scenario: Different assumption
- **WHEN** a suppressed polygon stores area 2 and estimated residents 20
- **THEN** the explanation identifies the applied estimate density as 10, rather than hardcoding the default 5

#### Scenario: Zero-area polygon
- **WHEN** a suppressed polygon has area 0
- **THEN** the popup identifies the total as estimated without displaying invalid or invented assumption values

### Requirement: Identify population source meaning
Population details SHALL identify the data as based on declared residence and resident totals as estimates. The interface SHALL NOT claim live population, observed headcounts, district totals or bin service catchments. It SHALL NOT invent a source year when none is stored.

#### Scenario: Explain the overlay
- **WHEN** an administrator opens a population popup
- **THEN** Lithuanian text explains declared residence and estimated totals
- **AND** it makes no claim about current physical presence or a bin's residents
