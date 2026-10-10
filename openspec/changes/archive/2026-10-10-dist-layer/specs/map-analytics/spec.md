# Spec Delta

## ADDED Requirements

### Requirement: Read-only district boundary map response
`GET /map-analytics/district-boundaries` SHALL return an unpaginated GeoJSON FeatureCollection of all stored district boundaries in ascending database ID order. Each feature SHALL have its database ID, stored Polygon geometry in longitude/latitude with all rings, and only `district_name` in its properties. Reads SHALL preserve all stored data.

#### Scenario: Read the supplied district catalog
- **WHEN** the supplied dataset has been imported and the endpoint is requested
- **THEN** the response contains 21 uniquely identified Polygon features with their stored names and coordinates
- **AND** it exposes no source path, `OBJECTID`, `NR`, area, perimeter, collection data or other unrelated metadata

#### Scenario: Read irregular shapes and holes
- **WHEN** stored boundaries include irregular Polygons or interior rings
- **THEN** the response preserves their rings rather than returning bounding boxes, centroids or simplified replacements

#### Scenario: Empty district catalog
- **WHEN** no district boundaries are stored
- **THEN** the endpoint returns HTTP 200 with a FeatureCollection whose features array is empty

### Requirement: District map reads use only stored data
District map requests SHALL read `district_boundaries` from PostgreSQL through the existing read-only collection contract. They SHALL NOT read or import the source GeoJSON, rebuild boundaries or fall back to a file. An unavailable database SHALL produce a failed read rather than a successful empty collection.

#### Scenario: Source unavailable after import
- **WHEN** stored boundaries exist and the source GeoJSON has been removed or is unreadable
- **THEN** district map requests still return the stored catalog without source-file access

#### Scenario: Source changes without import
- **WHEN** the source file is changed but no import command is invoked
- **THEN** district responses retain the previously stored names and geometries

#### Scenario: Database read fails
- **WHEN** the database is unavailable or the district query fails
- **THEN** the endpoint returns HTTP 500 using the existing collection-read error behavior
- **AND** no file fallback or fabricated empty success response is returned

### Requirement: Lithuanian district layer presentation
District names SHALL retain their Lithuanian spelling and diacritics in API `district_name` for district identity and stable color assignment. The district overlay SHALL NOT render these names as map labels. The layer option SHALL be `Seniūnijos`; its loading, empty, failure and retry feedback SHALL use the existing Lithuanian layer controls. The interface SHALL NOT invent a source date or describe boundaries as predicted or live data.

#### Scenario: Retain imported district identity without name labels
- **WHEN** the response contains `Žirmūnai`, `Šnipiškės` and `Grigiškės`
- **THEN** those names retain their district color assignments
- **AND** the district overlay displays their areas and boundaries without name labels

#### Scenario: District loading failure
- **WHEN** the selected district dataset cannot be loaded
- **THEN** its controls display `Nepavyko įkelti sluoksnio.` and the existing `Bandyti dar kartą` action
- **AND** the basemap and other selected layers remain usable
