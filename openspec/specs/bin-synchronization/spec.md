# bin-synchronization Specification

## Purpose

Maintain VipTop's collection-site registry from the Vilnius public GIS source while preserving operational history and allowing the backend to operate with its last stored data when synchronization fails.

Source: [Vilnius installed collection sites, layer 29](https://opencity.idvilnius.lt/gis/rest/services/Miesto_tvark/Miesto_tvarkymas_public/MapServer/29).

## Requirements

### Requirement: Retrieve the public site registry completely
The system SHALL retrieve the public layer 29 collection sites with `KAIKS_NR`, `ADRESAS`, and GeoJSON geometry in geographic coordinates using output reference 4326. Retrieval SHALL include all response pages before publishing updates. A server record limit SHALL NOT silently truncate a successful synchronization.

#### Scenario: Import a dataset spanning multiple pages
- **WHEN** the GIS response indicates more records after the first page
- **THEN** synchronization retrieves subsequent pages and considers all returned features before publishing updates

#### Scenario: Preserve data when a later page fails
- **WHEN** an earlier page succeeds but a later page fails
- **THEN** synchronization reports failure and leaves every existing Bin value unchanged

### Requirement: Map site identity and coordinates
For Polygon geometry, synchronization SHALL use the first coordinate of the first ring. For MultiPolygon geometry, it SHALL use the first coordinate of the first ring of the first polygon. Coordinates SHALL be interpreted as `[longitude, latitude]`. `properties.KAIKS_NR` SHALL supply Bin ID; `properties.ADRESAS` SHALL supply its address.

#### Scenario: Map a Polygon without swapping axes
- **WHEN** a Polygon for `KAIKS_NR` 15 has first-ring first coordinate `[25.296310700159605, 54.70261184373922]`
- **THEN** Bin 15 stores longitude 25.296310700159605 and latitude 54.70261184373922

#### Scenario: Map a MultiPolygon
- **WHEN** a MultiPolygon has a usable first coordinate in its first polygon's first ring
- **THEN** that coordinate supplies longitude and latitude using the same axis meanings as a Polygon

### Requirement: Skip unusable external features
Synchronization SHALL skip and log features whose `KAIKS_NR` is not a usable integer ID, whose geometry is missing or unsupported, or whose selected coordinate is empty, nonnumeric, nonfinite, or outside geographic bounds. Other valid features SHALL remain eligible for synchronization. A skipped feature SHALL NOT change an existing Bin.

#### Scenario: Skip a feature with a missing identifier
- **WHEN** one feature lacks a usable `KAIKS_NR` while another is valid
- **THEN** the invalid feature is skipped with its reason logged and the valid feature remains eligible for import

#### Scenario: Leave an existing site unchanged after invalid geometry
- **WHEN** an external feature identifies a stored Bin but has unusable geometry
- **THEN** its existing coordinates and address remain unchanged and the issue is logged

### Requirement: Represent missing addresses explicitly
For an otherwise usable feature, synchronization SHALL store a missing, blank, or nontext `ADRESAS` as `NULL` and log the address issue. It SHALL NOT discard the site or invent an address. A nonblank text address SHALL be retained as text.

#### Scenario: Insert a site without a source address
- **WHEN** a new usable feature has no `ADRESAS`
- **THEN** the Bin is inserted with its external ID and coordinates, its address is `NULL`, and the address issue is logged

#### Scenario: Clear a previously known address when the source omits it
- **WHEN** a usable feature for an existing Bin now has a blank address
- **THEN** its synchronized address becomes `NULL`

### Requirement: Upsert by external identity
Synchronization SHALL insert new Bins and update only `lat`, `lon`, and `address` on existing Bins identified by `KAIKS_NR`. Repeated synchronization of identical source data SHALL preserve one Bin per external ID with the same stored values.

#### Scenario: Insert a new site
- **WHEN** a valid source feature has an ID not present in storage
- **THEN** one Bin is inserted with that external ID and mapped values

#### Scenario: Update an existing site's attributes
- **WHEN** a valid feature for an existing ID changes its coordinates or address
- **THEN** those Bin values are updated without replacing its identity

#### Scenario: Repeat the same import
- **WHEN** the same valid registry is synchronized twice
- **THEN** the second run does not create duplicate Bins or change their stored values

### Requirement: Reject ambiguous source identities
If multiple usable source features in one retrieval share a `KAIKS_NR`, synchronization SHALL fail clearly and leave the existing registry unchanged rather than arbitrarily choosing one feature.

#### Scenario: Detect duplicate site IDs across pages
- **WHEN** two usable features on different pages have the same `KAIKS_NR`
- **THEN** the run fails, logs the duplicated identifier, and publishes no Bin updates

### Requirement: Retain absent sites and preserve operational records
Synchronization SHALL leave stored Bins absent from a later source response untouched. It SHALL NOT create, update, or delete Trucks, Routes, RouteStops, or ServiceEvents. Existing routing and service references SHALL survive changes to a Bin's address or coordinates.

#### Scenario: Retain a site omitted by the source
- **WHEN** a stored Bin does not occur in the latest complete response
- **THEN** the Bin and any historical references remain intact

#### Scenario: Preserve historical references during an update
- **WHEN** synchronization changes a Bin used by a stored stop and service event
- **THEN** their IDs, references, and recorded facts remain unchanged

### Requirement: Publish updates atomically and isolate failures
A synchronization failure SHALL preserve all previously committed Bin data, log the failure, and allow the running backend to continue. Failed source requests, malformed collection responses, source error payloads, and database write failures SHALL NOT publish partial updates. Source requests SHALL have timeouts.

#### Scenario: Handle unavailable GIS
- **WHEN** the source is unavailable or a request times out
- **THEN** the run reports failure, existing Bins remain unchanged, and the backend continues operating

#### Scenario: Reject a source error disguised as a response
- **WHEN** the source returns an error payload or a response that is not a usable GeoJSON FeatureCollection
- **THEN** the run fails rather than treating the payload as an empty registry

#### Scenario: Roll back a write failure
- **WHEN** a database error occurs after some updates have been attempted
- **THEN** none of that run's Bin changes are committed and prior data remains intact

### Requirement: Preserve data on empty or wholly unusable collections
If a complete source collection is empty or has no usable features after per-feature validation, synchronization SHALL leave the existing registry unchanged and report a warning. It SHALL NOT clear stored data or manufacture fallback sites.

#### Scenario: Handle an empty collection
- **WHEN** the source returns a valid empty FeatureCollection
- **THEN** no Bin changes occur and the run warns that there were no usable features

#### Scenario: Handle a collection containing only invalid features
- **WHEN** all retrieved features are skipped
- **THEN** no Bin changes occur and diagnostics report the skipped features and absence of usable data

### Requirement: Synchronize on startup and periodically
The backend SHALL attempt initial bin synchronization after schema preparation and before serving requests. Whether that attempt succeeds or fails, it SHALL schedule further attempts approximately every 24 hours after the preceding attempt completes. A restart SHALL trigger another initial attempt. A failed initial synchronization SHALL NOT by itself prevent request serving.

#### Scenario: Start with an available source
- **WHEN** the backend starts with its schema ready and the source available
- **THEN** it attempts an initial synchronization before serving requests and schedules the next attempt

#### Scenario: Start with unavailable GIS and an existing registry
- **WHEN** the backend starts with existing Bins but GIS retrieval fails
- **THEN** it logs the failure, serves using stored data, and retains the periodic schedule

#### Scenario: Start with unavailable GIS and no existing sites
- **WHEN** the schema is ready but initial retrieval fails against an empty registry
- **THEN** the backend starts with an empty registry, reports the failed import, and schedules later attempts

#### Scenario: Continue after a periodic failure
- **WHEN** a scheduled attempt fails
- **THEN** the backend continues serving and schedules another attempt after the configured interval

### Requirement: Own the scheduled synchronization lifecycle
Within the supported single-worker deployment, automatic synchronization attempts SHALL run sequentially without overlapping each other or blocking request handling during periodic work. Backend shutdown SHALL stop scheduling new runs and settle any in-flight synchronization before releasing its database resources.

#### Scenario: Handle requests during a periodic import
- **WHEN** a periodic import is waiting for GIS or writing Bins
- **THEN** unrelated backend requests can continue to be handled

#### Scenario: Stop the backend during synchronization
- **WHEN** shutdown starts while synchronization is in flight
- **THEN** no new automatic run is started and the in-flight operation is settled without partially committed Bin updates before its resources are released

### Requirement: Provide repeatable synchronization and diagnostics
An operator command SHALL run one synchronization using the same mapping and update behavior as the automatic runs. It SHALL report retrieved, skipped, and upserted feature counts, returning zero for a completed run and nonzero for a failed run. Automatic runs SHALL log equivalent summaries and failure reasons. A completed run with skipped features or no usable data SHALL still expose its warnings.

#### Scenario: Inspect a successful manual import
- **WHEN** an operator invokes one synchronization successfully
- **THEN** the command reports feature counts and exits zero

#### Scenario: Inspect a failed manual import
- **WHEN** an operator invokes synchronization and retrieval or writing fails
- **THEN** the command reports the reason, exits nonzero, and preserves the previous registry

#### Scenario: Inspect a completed run with skipped data
- **WHEN** retrieval completes with invalid features skipped and the remaining usable data is committed
- **THEN** diagnostics distinguish retrieved, skipped, and upserted counts, expose the skipped-feature warnings, and the manual command exits zero
