# Spec Delta

## MODIFIED Requirements

### Requirement: Collection site records
The system SHALL persist Bin records with only `id`, `lat`, `lon`, `address`, `type`, and `greening`. The ID SHALL be the external integer `KAIKS_NR` and SHALL NOT be generated. A Bin SHALL represent one collection site. Coordinates SHALL be required finite geographic degrees, with latitude in [-90, 90] and longitude in [-180, 180]. An unknown address SHALL be represented as `NULL`.

#### Scenario: Persist a collection site
- **WHEN** a site with external ID 634, latitude 54.6872, longitude 25.2797, and a known address is persisted
- **THEN** its Bin ID is 634 and its latitude, longitude, and address retain their respective meanings

#### Scenario: Reject unusable stored coordinates
- **WHEN** a Bin write supplies a missing coordinate, a nonfinite value, latitude outside [-90, 90], or longitude outside [-180, 180]
- **THEN** the write is rejected without changing existing records

#### Scenario: Preserve a site without an address
- **WHEN** a usable site has no address
- **THEN** its Bin can be stored with an unknown address and required coordinates

### Requirement: Schema readiness before serving
Standard backend startup SHALL prepare the versioned collection schema before serving requests. Repeating preparation on an up-to-date database SHALL preserve existing records. If schema preparation fails, the backend SHALL NOT begin serving requests. Schema preparation SHALL NOT import external Bin data.

#### Scenario: Start against an empty database
- **WHEN** the backend is started through its documented startup path against an empty configured database
- **THEN** the five collection tables and their constraints are available before request serving
- **AND** the Bin registry remains empty until an operator explicitly imports sites

#### Scenario: Restart against an initialized database
- **WHEN** the backend restarts with the current schema and existing collection records
- **THEN** schema preparation preserves those records without triggering a Bin import

#### Scenario: Refuse startup after schema preparation failure
- **WHEN** required schema preparation fails
- **THEN** startup reports the failure and does not launch request serving

## ADDED Requirements

### Requirement: Optional site metadata text
Bin `type` and `greening` SHALL each accept arbitrary text or `NULL`. Storage SHALL NOT restrict either field to a fixed list of labels or require a referenced classification record. These fields SHALL describe source site attributes rather than predicted fill or derived analytical features.

#### Scenario: Persist recognized Lithuanian labels
- **WHEN** a Bin is written with type `B3 (pusiau požeminiai)` and greening `Taip, agentūrai ES pritarus`
- **THEN** both supplied strings are retained with their Lithuanian characters

#### Scenario: Accept labels outside the known GIS mappings
- **WHEN** a valid Bin is written with type `Future collection-site type` and greening `Future greening description`
- **THEN** both strings are accepted without an allowed-value rejection

#### Scenario: Represent unknown metadata
- **WHEN** a valid Bin is written without type and greening information
- **THEN** both fields can be `NULL` while its required ID and coordinates remain present

#### Scenario: Upgrade existing collection records
- **WHEN** existing collection storage is upgraded to include the optional metadata fields before another import
- **THEN** existing Bins have `NULL` metadata while their IDs, coordinates, and addresses remain unchanged
- **AND** all existing truck, route, stop, and service-event records and references are preserved
