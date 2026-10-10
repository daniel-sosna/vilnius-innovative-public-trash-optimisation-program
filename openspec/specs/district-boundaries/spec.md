# district-boundaries Specification

## Purpose

Maintain a database catalog of named Vilnius seniūnija boundaries from an explicitly imported source dataset, independent of source-file availability during map use.

## Requirements

### Requirement: Explicit district boundary import
Operators SHALL be able to invoke `python -m app.interfaces.district_boundaries` natively or in the backend container. It SHALL accept `--file`, defaulting to `vilnius_seniuniju_ribos.geojson` in the configured data directory. Application startup, migrations and map requests SHALL NOT import boundaries.

#### Scenario: Import the supplied district dataset
- **WHEN** an operator explicitly invokes the district import with the supplied GeoJSON
- **THEN** the database contains one boundary for each of its 21 seniūnijos
- **AND** the command reports its source path and imported district count

#### Scenario: Select an explicit input
- **WHEN** an operator supplies `--file /some/path/districts.geojson`
- **THEN** the command reads that file instead of the configured default

#### Scenario: Start without importing
- **WHEN** the backend starts or a migration creates the boundary table while the source is present
- **THEN** no district records are imported automatically

### Requirement: Validate the boundary collection before replacement
The district import SHALL reject unreadable input, invalid JSON, a root other than a nonempty GeoJSON FeatureCollection, malformed features, missing or blank `SENIUNIJA`, and duplicate district names or source identifiers. Validation failure SHALL leave stored data unchanged and identify the offending input without disclosing database credentials.

#### Scenario: Reject an invalid final feature
- **WHEN** earlier features are valid but the final feature has no district name
- **THEN** the command fails and all previously stored district records remain unchanged

#### Scenario: Reject duplicate districts
- **WHEN** two input features repeat a district name or `OBJECTID`
- **THEN** the command rejects the collection rather than inserting multiple rows for that identity

#### Scenario: Reject an empty source
- **WHEN** the input FeatureCollection contains no features
- **THEN** the import fails without clearing the district catalog

### Requirement: Preserve valid district Polygon geometry
Each imported geometry SHALL be a nondegenerate two-dimensional Polygon with finite longitude/latitude coordinates, valid coordinate ranges and closed rings of at least four positions. All rings SHALL be preserved. Unsupported geometry types or coordinate systems SHALL fail without silently changing coordinates, discarding holes or replacing shapes with bounding boxes.

#### Scenario: Preserve an irregular boundary
- **WHEN** Vilkpėdė is imported from the supplied source
- **THEN** its stored boundary follows the supplied irregular Polygon rather than its bounding box

#### Scenario: Preserve holes
- **WHEN** a valid input Polygon contains interior rings
- **THEN** all those rings are retained in the stored geometry

#### Scenario: Reject projected or invalid positions
- **WHEN** a Polygon has projected coordinates outside longitude/latitude ranges, non-finite values, an unclosed ring or a non-Polygon geometry
- **THEN** the import fails and stored boundaries remain unchanged

### Requirement: Persist one named boundary per source district
Imported boundaries SHALL be stored in `district_boundaries`, with a database identity, `district_name` from `SENIUNIJA` and geometry that can be returned faithfully as GeoJSON. Lithuanian names SHALL retain their source spelling and diacritics. Storage SHALL NOT require the source file to remain available.

#### Scenario: Read a named imported district
- **WHEN** the supplied Žirmūnai feature has been imported
- **THEN** its stored record retains the name `Žirmūnai` and the source Polygon coordinates

#### Scenario: Remove the import source after success
- **WHEN** the source file is unavailable after a successful import
- **THEN** the stored district names and geometries remain available to database readers

### Requirement: Repeatable atomic district replacement
A successful district import SHALL replace the district catalog with exactly the input district set in one transaction, removing stale districts and avoiding duplicate accumulation. A failed replacement SHALL preserve the previous catalog. Standalone import SHALL leave collection data and existing population polygons unchanged.

#### Scenario: Import the same source twice
- **WHEN** the supplied file is successfully imported twice
- **THEN** the catalog still contains exactly 21 districts with the same names and geometries

#### Scenario: Replace an older catalog
- **WHEN** a valid new input omits a district from the previously imported set
- **THEN** that stale district is absent after successful replacement

#### Scenario: Fail during database insertion
- **WHEN** a database error occurs during district replacement
- **THEN** the previous catalog and all unrelated tables remain unchanged

### Requirement: Standalone district import exit codes
The standalone district command SHALL exit with 0 after a successful import and with 1 when its required file is missing, unreadable or invalid, or the database import fails. Failure output SHALL explain the cause without reporting a successful empty import.

#### Scenario: Missing standalone input
- **WHEN** the district command is invoked and its selected source file does not exist
- **THEN** it reports the missing path, exits with 1 and preserves the stored catalog

#### Scenario: Successful standalone input
- **WHEN** the supplied dataset is successfully committed
- **THEN** the command reports 21 imported districts and exits with 0
