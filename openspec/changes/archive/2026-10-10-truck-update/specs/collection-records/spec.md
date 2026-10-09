# Spec Delta

## MODIFIED Requirements

### Requirement: Truck records
The system SHALL persist Truck records with only `id`, `name`, `max_volume_m3`, `waste_carrier`, `landfill_id`, `available` and `deleted`. All fields except the transitional landfill reference SHALL be required. ID SHALL be generated. Name SHALL be nonempty after trimming. Maximum volume SHALL be positive finite numeric cubic metres, permitting fractions without a 99 limit. Carrier SHALL be normal text. Availability SHALL be boolean for future route generation. Deletion SHALL be boolean defaulting to false; deleted trucks SHALL always be unavailable.

#### Scenario: Persist truck capacity and availability
- **WHEN** a truck named `Šiukšliavežė 3` is stored with maximum volume 18.5, carrier `Ecoservice` and availability true
- **THEN** the truck retains its generated ID, maximum volume 18.5 m³, carrier and availability, and has no `max_bins_per_trip` field

#### Scenario: Reject unusable truck capacity
- **WHEN** a truck write supplies zero, a negative, missing or nonfinite maximum volume
- **THEN** the write is rejected

#### Scenario: Enforce the upper capacity bound
- **WHEN** an otherwise valid truck write supplies maximum volume 120
- **THEN** it is stored as 120 m³ because the former site-count upper bound no longer applies to volume

#### Scenario: Reject an empty truck name
- **WHEN** a truck write supplies an empty or whitespace-only name
- **THEN** the write is rejected

#### Scenario: Default a new truck's deletion flag
- **WHEN** a valid new truck is stored without explicitly supplying its deletion flag
- **THEN** its stored deletion flag is false

#### Scenario: Reject inconsistent retired-truck availability
- **WHEN** a truck write would store deleted true and available true together
- **THEN** the write is rejected

## ADDED Requirements

### Requirement: Open-ended truck carrier storage
Truck carrier storage SHALL accept normal text beyond the four companies offered by the current UI. The database SHALL NOT use an enum, CHECK constraint, foreign-key catalog or other constraint to limit possible carrier names. A carrier SHALL be required, with nonblank mutation validation belonging to the application.

#### Scenario: Store a future carrier
- **WHEN** an otherwise valid truck is persisted with carrier `Kitas vežėjas`
- **THEN** storage accepts and retains that text without changing the schema or an allowed-values catalog

#### Scenario: Inspect carrier storage
- **WHEN** the truck schema is inspected
- **THEN** carrier uses an ordinary required text column without any database constraint restricting possible names

### Requirement: Guard the truck volume schema transition
The volume/carrier upgrade SHALL require an empty legacy truck table, including retired records. It SHALL remove site-count capacity, prepare required volume/carrier storage and preserve collection data and truck identity generation. If any legacy truck exists, preparation SHALL fail with actionable IDs and an explanation without changing its data or publishing a partial upgrade.

#### Scenario: Upgrade the confirmed empty fleet
- **WHEN** initialized collection storage has no trucks and the volume/carrier upgrade runs
- **THEN** required volume/carrier storage replaces site-count capacity and existing sites, bins, history and import bookkeeping retain their values and references

#### Scenario: Detect unexpected legacy trucks
- **WHEN** the legacy table contains an available, unavailable or retired truck at upgrade time
- **THEN** preparation fails identifying affected truck IDs and explaining that site counts cannot be converted to volume and carriers are unknown
- **AND** the old schema and records remain intact until the incompatibility is deliberately resolved

#### Scenario: Prepare fresh storage
- **WHEN** storage is initialized from empty through the documented startup path
- **THEN** the final Truck model has the seven specified fields, with a nullable landfill reference and no external data is fetched

#### Scenario: Repeat preparation after creating trucks
- **WHEN** schema preparation runs again after this upgrade and volume-based trucks have been created
- **THEN** their values and retirement flags remain unchanged without rerunning the legacy empty-table guard

### Requirement: Seed the supplied landfill catalog
The system SHALL seed `landfills` with the three supplied GeoJSON features, generated integer IDs starting at 1, original IDs retained separately and separate latitude/longitude. It SHALL preserve every property and collection name/description, excluding all `type` fields. Missing properties SHALL remain null. Supplied provenance SHALL not imply independent operational verification.

#### Scenario: Preserve every supplied facility
- **WHEN** fresh storage is prepared from the supplied catalog snapshot
- **THEN** three records have generated IDs 1–3 in file order, original source IDs, all exact property/array values and collection metadata, with longitude/latitude mapped correctly and no type fields
- **AND** the next generated landfill ID is 4

#### Scenario: Preserve absent source properties
- **WHEN** a feature omits `current_status_source` or `municipal_arrangement_source`
- **THEN** the corresponding stored column is null without fabricated content

#### Scenario: Repeat preparation without external access
- **WHEN** startup migration runs again without the original Downloads file or network access
- **THEN** the seeded catalog remains unchanged and no duplicates or external requests occur

### Requirement: Optional landfill details
Landfill storage SHALL require only generated `id` and `name`; all source metadata, coordinates and other facility detail columns SHALL permit null. Relaxing required details SHALL preserve supplied values and Truck references. Nonnull source IDs SHALL remain unique and supplied coordinates SHALL remain within geographic ranges. Rollback to required detail fields SHALL refuse incomplete rows without filling or discarding their data.

#### Scenario: Store a named facility with unknown details
- **WHEN** a facility is stored with only its name
- **THEN** it receives a generated integer ID and every detail column is null

#### Scenario: Preserve the supplied catalog while relaxing fields
- **WHEN** revision 0006 storage is upgraded for nullable landfill details
- **THEN** all seeded values and Truck references remain unchanged

#### Scenario: Refuse lossy nullable-field rollback
- **WHEN** rollback would require a detail field that is null in a stored facility
- **THEN** preparation fails identifying affected facility IDs without changing schema, records or migration version

### Requirement: Preserve existing trucks during landfill preparation
Landfill preparation SHALL add a nullable Truck reference without inventing assignments or changing existing Truck, collection or import data. A nonnull reference SHALL identify an existing landfill. A referenced landfill SHALL not be deleted. Rollback SHALL refuse to discard any assignment, including a retired truck's assignment, without changing storage.

#### Scenario: Upgrade a populated volume-based fleet
- **WHEN** the landfill migration runs with active and retired trucks at the volume schema
- **THEN** their fields and collection/import records remain unchanged, and their landfill references are null

#### Scenario: Enforce a landfill reference
- **WHEN** a stored Truck references a nonexistent landfill or deletion targets a referenced landfill
- **THEN** storage rejects the operation and preserves the existing records

#### Scenario: Guard assignment rollback
- **WHEN** landfill rollback is attempted with any assigned active or retired truck
- **THEN** it fails identifying affected trucks before changing schema or records

#### Scenario: Roll back unassigned storage
- **WHEN** landfill rollback runs with only unassigned trucks
- **THEN** landfill storage and references are removed while original Truck and collection/import values remain unchanged
