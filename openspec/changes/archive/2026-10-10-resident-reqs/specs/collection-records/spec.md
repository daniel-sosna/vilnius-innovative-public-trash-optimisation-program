# Spec Delta

## ADDED Requirements

### Requirement: Minimal resident-request records
The system SHALL persist `ResidentRequest` records in `resident_requests` with only generated BIGINT primary key `id`, required BIGINT `bin_id` referencing internal `bins.id`, and required timezone-naive `timestamp`. Each Bin SHALL expose its resident requests, and each request SHALL reference its Bin. Records SHALL contain no user identity, IP address, device information, security metadata, or derived values.

#### Scenario: Persist a resident report
- **WHEN** a valid request is created for an existing bin
- **THEN** it receives an independently generated ID and stores only that ID, the bin's internal ID, and its submission timestamp
- **AND** it remains retrievable after restarting the backend while its bin exists

#### Scenario: Reject a missing or nonexistent parent
- **WHEN** a resident-request write omits `bin_id` or references a bin that does not exist
- **THEN** storage rejects the write without creating a detached record

#### Scenario: Preserve separate requests at the same local time
- **WHEN** two valid requests target the same bin with identical timestamps
- **THEN** both can be stored under different generated IDs

#### Scenario: Refresh a surviving bin
- **WHEN** synchronization updates a bin's metadata or site membership while preserving its internal identity
- **THEN** the bin's existing resident requests retain their IDs, references, and timestamps

### Requirement: Vilnius local submission timestamps
Resident-request timestamps SHALL be generated on the server from the current Europe/Vilnius local clock and stored as `TIMESTAMP WITHOUT TIME ZONE`. They SHALL contain no timezone or offset and SHALL NOT depend on the resident device's clock or the server/database default timezone. Missing timestamps SHALL be rejected. Request creation SHALL preserve existing service-history timestamp values.

#### Scenario: Use Vilnius time with a UTC server
- **WHEN** a request is submitted when Vilnius local time is `2026-10-09 15:30:00` and the server and database sessions use UTC
- **THEN** its stored timestamp represents `2026-10-09 15:30:00`, with permitted fractional seconds and no timezone or offset
- **AND** the device's timezone does not affect the result

#### Scenario: Use the timezone's current seasonal clock
- **WHEN** requests are submitted during the summer and winter clock periods
- **THEN** each timestamp records the Europe/Vilnius local time applicable at submission, without assuming a fixed UTC offset

#### Scenario: Reject an absent timestamp
- **WHEN** a resident-request write supplies no usable timestamp and no server-generated value
- **THEN** storage rejects the write

### Requirement: Additive resident-request schema upgrade
The versioned schema upgrade SHALL add resident-request storage without deleting, replacing, reseeding, or changing existing collection records, trucks, identities, or import checkpoints. Schema preparation SHALL preserve saved requests on repeated startup and SHALL NOT import external data. Removing only this feature's schema SHALL leave existing collection storage intact.

#### Scenario: Upgrade initialized collection storage
- **WHEN** the upgrade runs against storage already at revision `0004`
- **THEN** resident-request storage becomes available and all existing sites, bins, bin history, trucks, and import progress retain their values and identities

#### Scenario: Repeat schema preparation
- **WHEN** startup prepares a schema that already contains resident requests
- **THEN** the requests and other records remain unchanged and no import or cleanup starts

#### Scenario: Prepare a fresh database
- **WHEN** the documented backend startup prepares empty storage through the current schema
- **THEN** resident-request storage is ready before the backend serves requests, alongside existing collection storage

#### Scenario: Remove the feature schema
- **WHEN** the resident-request upgrade alone is rolled back
- **THEN** resident-request storage is removed, and existing collection tables, records, and identities remain intact

## MODIFIED Requirements

### Requirement: Collection deletion rules
Storage SHALL reject deleting a Site that still has bins. Removing a Bin during successful bounded refresh cleanup SHALL also remove its BinHist records. Every Bin deletion SHALL cascade deletion to its resident requests. Truck soft deletion SHALL retain the truck row and SHALL NOT change sites, bins, bin history, or resident requests.

#### Scenario: Preserve a referenced site
- **WHEN** direct deletion is requested for a Site with surviving bins
- **THEN** deletion is rejected and its bins remain attached

#### Scenario: Remove a bin and its history together
- **WHEN** successful bounded refresh cleanup removes a missing Bin
- **THEN** that Bin, all its history, and all its resident requests are removed together
- **AND** its Site is removed only if no member bins remain

#### Scenario: Soft delete a truck
- **WHEN** a truck is retired through the management API
- **THEN** its row remains deleted and unavailable and all sites, bins, history, and resident requests remain unchanged

#### Scenario: Cascade a direct bin deletion
- **WHEN** a Bin with resident requests is deleted directly
- **THEN** its resident requests are removed in the same transaction without requiring application-side cleanup
- **AND** requests belonging to other surviving bins remain unchanged

#### Scenario: Roll back a bin deletion
- **WHEN** a transaction deleting a Bin and its resident requests fails or is rolled back
- **THEN** the Bin and its requests remain stored together
