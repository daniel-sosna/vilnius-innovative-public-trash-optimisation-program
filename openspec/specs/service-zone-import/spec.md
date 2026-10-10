# service-zone-import Specification

## Purpose

Let developers populate and refresh Vilnius waste collection service zones from a validated GeoJSON import source, preserving stored data when an import fails.

## Requirements

### Requirement: Explicit manual zone import
`python -m app.interfaces.service_zones` SHALL import service zones only on explicit invocation, using the existing database configuration both natively and inside the backend container. Application startup, migrations and map reads SHALL NOT run this import.

#### Scenario: Invoke the dedicated command
- **WHEN** the developer explicitly runs the command with a valid input and reachable database
- **THEN** stored service zones are replaced by the input dataset
- **AND** collection, population, landfill and truck records are unchanged

#### Scenario: Start the application with source data present
- **WHEN** the application starts or migrations run while the source file exists
- **THEN** service-zone records are not imported or replaced automatically

### Requirement: Configurable zone import source
The dedicated command SHALL accept `--file`. Without it, the input SHALL be `service_zones.geojson` in the existing configured data directory: `VIPTOP_DATA_DIR` when set, otherwise `backend/data/`; relative configured paths resolve from the repository root. In Docker the default SHALL use the mounted data directory.

#### Scenario: Default source
- **WHEN** the command runs without `--file`
- **THEN** it reads the canonical filename in the configured data directory

#### Scenario: Explicit file
- **WHEN** the developer supplies `--file /some/path/zones.geojson`
- **THEN** that file is used instead of the default source

#### Scenario: Shared directory inside Docker
- **WHEN** Compose mounts the shared data folder into the backend and the command runs without `--file`
- **THEN** it reads the canonical source from that mounted folder

### Requirement: Validate zone features before replacement
The importer SHALL accept a GeoJSON FeatureCollection of Polygon features with nonblank string `ZONA`, unique integer `ZONOS_NR`, and finite longitude/latitude coordinates. Every ring SHALL contain at least four positions and close at the same position. Invalid JSON, unsupported geometry or coordinate reference, missing properties and invalid values SHALL cause failure before stored rows are replaced.

#### Scenario: Import the supplied dataset
- **WHEN** the supplied five-feature CRS84 dataset is imported
- **THEN** all five Polygon features pass validation and become stored zones

#### Scenario: Invalid feature after valid features
- **WHEN** a later feature has a missing name, duplicate zone number, open ring, non-finite coordinate or non-Polygon geometry
- **THEN** the entire input is rejected and stored zones remain unchanged

#### Scenario: Unsupported projected coordinates
- **WHEN** the source declares an unsupported projected coordinate reference or contains coordinates outside longitude/latitude ranges
- **THEN** the command fails without treating those coordinates as map positions

### Requirement: Faithful minimal service-zone records
Each imported feature SHALL produce one `service_zones` record with an identifier, `zone_name` from `properties.ZONA`, integer `zone_number` from `properties.ZONOS_NR`, and reconstructable geometry preserving every Polygon ring. Source labels SHALL retain their Lithuanian characters. Unnecessary source metadata SHALL NOT be persisted.

#### Scenario: Preserve source meaning
- **WHEN** a feature contains `ZONA: "Centrinė"` and `ZONOS_NR: 5`
- **THEN** the stored name is `Centrinė` and the stored number is integer 5
- **AND** its geometry matches the source and no dataset description or extra source properties are stored

#### Scenario: Preserve holes
- **WHEN** a valid Polygon contains an exterior ring and interior rings
- **THEN** all rings are retained for GeoJSON reconstruction

### Requirement: Atomic repeatable zone replacement
A successful dedicated import SHALL replace the complete service-zone dataset with exactly the supplied feature records. Repeated imports SHALL NOT accumulate duplicate zones, and zones removed from the source SHALL be removed from storage. Any import failure SHALL preserve the previously stored dataset.

#### Scenario: Repeat the supplied import
- **WHEN** the five-feature source is imported twice
- **THEN** the table contains five zones, each zone number appearing exactly once

#### Scenario: Refresh boundaries and membership
- **WHEN** a valid updated source changes a boundary and removes a zone
- **THEN** the new boundary is stored and the absent zone is removed

#### Scenario: Write failure
- **WHEN** a database failure occurs while replacing zones
- **THEN** all previous zone records remain unchanged

### Requirement: Dedicated import feedback
The dedicated command SHALL report its source and imported row count and exit with 0 on success. Missing or unreadable input, invalid data or database failure SHALL produce a readable error without credentials, exit with 1 and leave stored data unchanged.

#### Scenario: Missing dedicated source
- **WHEN** the selected source file does not exist
- **THEN** the command fails clearly, exits with 1 and preserves existing zones

#### Scenario: Successful summary
- **WHEN** the supplied dataset is imported successfully
- **THEN** output identifies the source, reports five service zones and exits with 0
