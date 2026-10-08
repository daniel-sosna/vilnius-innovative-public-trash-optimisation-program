# bin-synchronization Specification

## Purpose

Maintain VipTop's collection-site registry from the Vilnius public GIS source while preserving operational history and allowing the backend to operate with its last stored data when synchronization fails.

Source: [Vilnius installed collection sites, layer 29](https://opencity.idvilnius.lt/gis/rest/services/Miesto_tvark/Miesto_tvarkymas_public/MapServer/29).

## Requirements

### Requirement: Retrieve the public site registry completely
The system SHALL retrieve the public layer 29 collection sites with all source attributes, including `KAIKS_NR`, `ADRESAS`, `TIPAS`, and `ZELDINIMAS`, and GeoJSON geometry using output reference 4326. Retrieval SHALL honor the configured query and include all response pages before publishing updates. A server record limit SHALL NOT silently truncate a successful synchronization.

#### Scenario: Import a dataset spanning multiple pages
- **WHEN** the GIS response indicates more records after the first page
- **THEN** synchronization retrieves subsequent pages and considers all returned features before publishing updates

#### Scenario: Preserve data when a later page fails
- **WHEN** an earlier page succeeds but a later page fails
- **THEN** synchronization reports failure and leaves every existing Bin value unchanged

#### Scenario: Use the supplied all-attributes query
- **WHEN** the configured layer query includes `outFields=*`, `resultRecordCount=50`, `where=1=1`, `returnGeometry=true`, `outSR=4326`, `f=geojson`, and `spatialRel=esriSpatialRelIntersects`
- **THEN** requests retain those parameters, start at offset 0, and advance offsets by 50 while either supported continuation flag reports more data
- **AND** retrieval uses stable OBJECTID ordering and includes sites after the first 50 records

#### Scenario: Advance after a short or empty intermediate page
- **WHEN** a requested 50-record page contains fewer records but still indicates continuation
- **THEN** the next offset advances by 50 rather than by the number of returned features

#### Scenario: Reject an unsupported pagination size
- **WHEN** a configured page size is not an integer in the supported range of 1 to 1,000 records
- **THEN** synchronization reports a workflow error and preserves every stored Bin value rather than risking an incomplete import

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
Synchronization SHALL insert new Bins and update only `lat`, `lon`, `address`, `type`, and `greening` on existing Bins identified by `KAIKS_NR`. Repeated synchronization of identical source data SHALL preserve one Bin per external ID with the same stored values.

#### Scenario: Insert a new site
- **WHEN** a valid source feature has an ID not present in storage
- **THEN** one Bin is inserted with that external ID and mapped values

#### Scenario: Update an existing site's attributes
- **WHEN** a valid feature for an existing ID changes its coordinates or address
- **THEN** those Bin values are updated without replacing its identity

#### Scenario: Repeat the same import
- **WHEN** the same valid registry is synchronized twice
- **THEN** the second run does not create duplicate Bins or change their stored values

#### Scenario: Update metadata on an existing site
- **WHEN** a usable feature changes the type or greening code for a stored Bin
- **THEN** synchronization updates its mapped metadata without replacing the Bin or changing its references

#### Scenario: Clear metadata when the source no longer supplies it
- **WHEN** a usable feature for a stored Bin now has missing or null type or greening information
- **THEN** the corresponding stored metadata becomes `NULL` while any other usable values are synchronized

### Requirement: Reject ambiguous source identities
If multiple usable source features in one retrieval share a `KAIKS_NR`, synchronization SHALL fail clearly and leave the existing registry unchanged rather than arbitrarily choosing one feature.

#### Scenario: Detect duplicate site IDs across pages
- **WHEN** two usable features on different pages have the same `KAIKS_NR`
- **THEN** the run fails, logs the duplicated identifier, and publishes no Bin updates

### Requirement: Retain absent sites and preserve operational records
Synchronization SHALL leave stored Bins absent from a later source response untouched. It SHALL NOT create, update, or delete Trucks, Routes, RouteStops, or ServiceEvents. Existing routing and service references SHALL survive changes to a Bin's coordinates, address, type, or greening.

#### Scenario: Retain a site omitted by the source
- **WHEN** a stored Bin does not occur in the latest complete response
- **THEN** the Bin and any historical references remain intact

#### Scenario: Preserve historical references during an update
- **WHEN** synchronization changes a Bin used by a stored stop and service event
- **THEN** their IDs, references, and recorded facts remain unchanged

#### Scenario: Retain metadata for an absent or skipped site
- **WHEN** a stored Bin is absent from the response or its feature is skipped for unusable identity or geometry
- **THEN** its existing type and greening remain unchanged along with its other Bin values

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

### Requirement: Provide repeatable synchronization and diagnostics
An operator command SHALL run one complete synchronization and exit without starting an application server or scheduling another import. It SHALL report retrieved, skipped, and upserted feature counts, returning zero for a completed run and nonzero for a failed run. A completed run with skipped features or no usable data SHALL still expose its warnings. Explicit reruns SHALL use the same mapping and upsert behavior.

#### Scenario: Inspect a successful manual import
- **WHEN** an operator invokes one synchronization successfully
- **THEN** the command reports feature counts and exits zero

#### Scenario: Inspect a failed manual import
- **WHEN** an operator invokes synchronization and retrieval or writing fails
- **THEN** the command reports the reason, exits nonzero, and preserves the previous registry

#### Scenario: Inspect a completed run with skipped data
- **WHEN** retrieval completes with invalid features skipped and the remaining usable data is committed
- **THEN** diagnostics distinguish retrieved, skipped, and upserted counts, expose the skipped-feature warnings, and the manual command exits zero

#### Scenario: End after one complete import
- **WHEN** an explicitly invoked command finishes retrieving all indicated pages and publishing its valid sites
- **THEN** it releases its database resources and exits without leaving an import timer or application server running

#### Scenario: Refresh only when requested again
- **WHEN** the operator explicitly invokes the command again after a previous successful import
- **THEN** a new complete import uses the same stable external identities and does not create duplicate Bins

### Requirement: Import only on explicit invocation
Bin synchronization SHALL run only when an operator explicitly invokes the import command. Application startup, restart, development reload, and idle runtime SHALL NOT fetch GIS data or schedule imports. The application SHALL serve with an empty or previously populated registry independently of GIS availability. Its shutdown SHALL NOT wait for an import process launched separately by an operator.

#### Scenario: Start before populating bins
- **WHEN** the backend starts after successful schema preparation against a database with no Bins
- **THEN** it serves requests with an empty registry and makes no GIS request
- **AND** no Bin is inserted until a successful explicit import

#### Scenario: Restart or reload without refreshing the registry
- **WHEN** a running backend is restarted or development reload occurs with stored Bins
- **THEN** no GIS request or import is triggered and all stored Bin values remain unchanged

#### Scenario: Remain idle without automatic imports
- **WHEN** the backend continues running without an operator invoking an import
- **THEN** it makes no GIS requests and does not refresh or populate Bins automatically

#### Scenario: Start while the source is unavailable
- **WHEN** schema preparation succeeds but the configured GIS source is unreachable
- **THEN** the backend serves requests without attempting the source or waiting for its HTTP timeout

#### Scenario: Populate bins after application setup
- **WHEN** schema preparation is complete and an operator explicitly invokes the import command
- **THEN** the command retrieves the complete configured registry and commits usable Bins according to the mapping and upsert requirements

#### Scenario: Keep import resource ownership independent
- **WHEN** backend shutdown occurs while a separately launched operator import is running
- **THEN** application shutdown does not coordinate with or wait for that import process
- **AND** the command retains responsibility for its own resource cleanup and atomic publication

### Requirement: Map source type codes to labels
Synchronization SHALL translate recognized integer `TIPAS` codes into the exact labels in the following scenario, storing the result in Bin `type`. It SHALL support the full ten-code mapping even when the current source contains only some of those codes.

#### Scenario: Translate each recognized type code
- **WHEN** a usable feature supplies a recognized integer `TIPAS`
- **THEN** its Bin type is the corresponding label:

| Code | Stored type |
|---|---|
| 1 | A1 (požeminiai) |
| 2 | A3 (požeminiai) |
| 3 | B2 (pusiau požeminiai stačiakampiai) |
| 4 | B3 (pusiau požeminiai) |
| 5 | C1 (pusiau požeminiai apvalūs) |
| 6 | C5 (pusiau požeminiai apvalūs) |
| 7 | D8 (dekoratyviniai apdangalai) |
| 8 | E3 (antžeminiai, pakeliamieji) |
| 9 | E4 (antžeminiai, įrengti pastate, atskirame statinyje) |
| 10 | F (pilnai nesukomplektuota aikštelė) |

### Requirement: Map source greening codes to labels
Synchronization SHALL translate recognized integer `ZELDINIMAS` codes into `Taip` for 1, `Ne` for 2, and `Taip, agentūrai ES pritarus` for 3, storing the result in Bin `greening`. It SHALL retain these text meanings rather than reducing the field to a boolean.

#### Scenario: Translate each recognized greening code
- **WHEN** a usable feature supplies `ZELDINIMAS` 1, 2, or 3
- **THEN** its Bin greening retains the corresponding exact Lithuanian label

### Requirement: Keep optional metadata failures nonfatal
Missing or null `TIPAS` or `ZELDINIMAS` SHALL map to `NULL`. An unrecognized or unusable non-null code SHALL map to `NULL` and produce a warning identifying the site, field, and raw value. An otherwise usable site SHALL still be imported; metadata warnings SHALL NOT increase the skipped-feature count or cause a nonzero manual-command exit.

#### Scenario: Import a site with no metadata
- **WHEN** a usable feature has missing or null type and greening properties
- **THEN** it is imported with `NULL` metadata without unknown-code warnings for the absent values

#### Scenario: Import a site with unknown numeric codes
- **WHEN** a usable feature has `TIPAS=99` and `ZELDINIMAS=99`
- **THEN** both metadata fields become `NULL`, both unknown codes are logged, and the site remains eligible for a successful upsert
- **AND** these warnings do not classify the feature as skipped

#### Scenario: Clear a known value after an unknown replacement
- **WHEN** a stored Bin has known metadata and a later usable feature supplies an unknown replacement code
- **THEN** the affected stored field becomes `NULL` and the warning is logged

#### Scenario: Reject metadata code coercion without rejecting the site
- **WHEN** a usable feature supplies a boolean, fractional number, text, or object as a metadata code
- **THEN** each affected field becomes `NULL` with a warning rather than being coerced into a recognized code
- **AND** valid identity, geometry, address, and other recognized metadata remain eligible for import

### Requirement: Obtain synchronization settings from configuration
The source URL and HTTP timeout SHALL be supplied through `.env` or environment variables rather than built-in runtime defaults. The timeout SHALL be a positive finite number; its documented example SHALL remain 30 seconds. Environment values SHALL take precedence over corresponding dotenv values. No synchronization interval setting SHALL be required or used.

#### Scenario: Override the timeout in the environment
- **WHEN** `.env` specifies an HTTP timeout of 30 seconds and the process environment specifies 5 seconds
- **THEN** the explicit import uses the environment timeout of 5 seconds

#### Scenario: Configure importing without an interval
- **WHEN** the required connection, source URL, and HTTP timeout are configured without an interval setting
- **THEN** configuration loads successfully and no automatic import is scheduled

#### Scenario: Run entirely from deployment environment variables
- **WHEN** the required connection and synchronization settings are present in the process environment and no dotenv file is available
- **THEN** configuration loads successfully without requiring a copied or mounted `.env` file

#### Scenario: Report missing configuration before operating
- **WHEN** a required synchronization setting is absent from both configuration sources
- **THEN** entry points that load the shared configuration report a configuration error rather than silently using a fallback, and the manual command exits nonzero

#### Scenario: Reject an invalid timeout
- **WHEN** a configured HTTP timeout is zero, negative, or nonfinite
- **THEN** configuration is rejected before synchronization begins

### Requirement: Load the shared dotenv file for native execution
Native backend entry points SHALL load the repository-root `.env` independently of the working directory and use the same settings contract for migration and explicit import. Unrelated keys in the shared file SHALL NOT make backend settings invalid. Configuration diagnostics SHALL NOT disclose the database connection's credentials.

#### Scenario: Invoke native commands from the backend directory
- **WHEN** valid settings are in the repository-root `.env` and native migration or import is invoked from `backend/`
- **THEN** the command obtains those settings without requiring the synchronization variables to be exported manually

#### Scenario: Read a shared file with PostgreSQL container settings
- **WHEN** the shared `.env` includes `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD` alongside backend settings
- **THEN** those unrelated keys do not cause an extra-field validation failure

#### Scenario: Override a container connection for native use
- **WHEN** `.env` contains a connection using hostname `db` and the native process environment supplies a valid localhost connection
- **THEN** native commands use the environment connection while obtaining other settings from `.env`
