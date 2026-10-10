# Spec Delta

## ADDED Requirements

### Requirement: Read-only service-zone map response
`GET /map-analytics/service-zones` SHALL return an unpaginated GeoJSON FeatureCollection of all stored service zones in ascending ID order. Each feature SHALL contain its identifier, Polygon geometry in longitude/latitude preserving all rings, and only `zone_name` and integer `zone_number` properties. Reads SHALL preserve stored data and existing map endpoints.

#### Scenario: Read the supplied stored zones
- **WHEN** the supplied five zones have been imported and the endpoint is requested
- **THEN** five uniquely identified Polygon features are returned, one per stored zone
- **AND** names are `Centrinė`, `Pietinė`, `Šiaurinė`, `Rytinė` and `Vakarinė`, with their corresponding stored numbers
- **AND** no `OBJECTID` property, source filename, source descriptions, population metrics or collection records are exposed

#### Scenario: Read all stored rings
- **WHEN** a stored zone contains interior rings
- **THEN** its geometry includes those rings unchanged

#### Scenario: Empty service-zone table
- **WHEN** no service zones are stored
- **THEN** the endpoint succeeds with a FeatureCollection containing an empty features array

### Requirement: Service-zone runtime independence from source files
Service-zone map reads SHALL query PostgreSQL and SHALL NOT read, re-import or fall back to the source GeoJSON at request time. The frontend SHALL obtain zone data from the backend API, never from the import file. Database failures SHALL follow the existing collection-read error contract rather than produce a successful empty or file-backed response.

#### Scenario: Source unavailable after import
- **WHEN** zones exist in PostgreSQL but the source GeoJSON is unavailable
- **THEN** the endpoint still returns the stored zones and the layer can load them through the API

#### Scenario: Source changes without an import
- **WHEN** the local source changes but no import runs
- **THEN** the endpoint continues to return the previously stored dataset

#### Scenario: Database read fails
- **WHEN** PostgreSQL cannot supply the service-zone dataset
- **THEN** the request reports a failed read and does not substitute file data or an empty success
