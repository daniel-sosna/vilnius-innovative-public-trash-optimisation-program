# collection-records Specification

## Purpose

Provide persistent collection-site, truck, route, stop, and service-observation records that future collection workflows and analytical consumers can use without duplicating operational facts.

## Requirements

### Requirement: Collection site records
The system SHALL persist Site records with `id`, `site_key`, `address`, `latitude`, and `longitude`, all required. Imported sites SHALL group bins by normalized registered address and derive coordinates from member-bin means during import. Manual sites SHALL have independent identity and explicitly selected coordinates. Coordinates SHALL be finite, latitude in [-90, 90] and longitude in [-180, 180]. Admin Bin addition/deletion SHALL preserve a surviving Site's stored coordinates.

#### Scenario: Persist a collection site
- **WHEN** physical bins with one registered address are imported
- **THEN** they reference one generated imported Site identity with a readable address and their mean coordinates

#### Scenario: Reject unusable stored coordinates
- **WHEN** a Site or Bin write supplies a missing, nonfinite, or geographically out-of-range coordinate
- **THEN** storage rejects the write without publishing its transaction

#### Scenario: Preserve a site without an address
- **WHEN** an imported bin has no registered address
- **THEN** its site has a readable fallback address and a deterministic key based on that bin's external ID
- **AND** it does not share a site with other unknown-address bins

#### Scenario: Persist an explicitly selected manual location
- **WHEN** an administrator creates a Site with a selected location and two initial Bins
- **THEN** Site and both Bins store the selected coordinates without inferring a location from address text
- **AND** those coordinates are described as selected, not an imported derived average

#### Scenario: Preserve an existing location during admin deletion
- **WHEN** an administrator deletes one of an imported Site's Bins and others remain
- **THEN** the Site retains its stored latitude/longitude and the remaining Bins retain their own coordinates

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

### Requirement: Required entity relationships
Each physical Bin SHALL reference exactly one existing Site through required `site_id`. Each BinHist SHALL reference one existing physical Bin through required `bin_id`. Sites SHALL expose their member bins and bins their historical attempts. No route or truck relationship SHALL be required by bin history.

#### Scenario: Reject a missing relationship
- **WHEN** a Bin lacks `site_id` or a BinHist lacks `bin_id`
- **THEN** storage rejects the write

#### Scenario: Reject a nonexistent parent
- **WHEN** a Bin or BinHist references a nonexistent parent
- **THEN** storage rejects the write without creating detached records

### Requirement: Preserve raw per-site history
The system SHALL preserve raw service attempts per physical Bin and permit chronological retrieval by timezone-naive `date`, with generated ID breaking ties. It SHALL NOT invent fill observations, service durations, truck attribution, intervals, predictions, or historical location snapshots. History SHALL remain available until its Bin is deliberately removed.

#### Scenario: Retrieve consecutive raw observations
- **WHEN** a Bin has attempts on 1 September and 4 September
- **THEN** both raw attempts can be retrieved in date order without persisted derived intervals

#### Scenario: Distinguish simultaneous event ordering
- **WHEN** a Bin has successful and unsuccessful attempts at the same timestamp
- **THEN** both remain stored and ID provides deterministic ordering for the tie

### Requirement: Schema readiness before serving
Standard backend startup SHALL prepare the versioned schema before serving requests and refuse serving if preparation fails. After the one-time destructive transition, repeated preparation SHALL preserve existing records. Schema preparation SHALL NOT import VASA data or run refresh cleanup.

#### Scenario: Start against an empty database
- **WHEN** the backend starts through its documented path against empty storage
- **THEN** sites, physical bins, bin history, trucks, and internal import bookkeeping are ready before serving
- **AND** no external data is fetched or imported

#### Scenario: Restart against an initialized database
- **WHEN** the backend restarts after the replacement migration has completed
- **THEN** existing data and checkpoints are preserved and no import or cleanup starts

#### Scenario: Refuse startup after schema preparation failure
- **WHEN** required schema preparation fails
- **THEN** startup reports failure and does not serve requests

### Requirement: Preserve collection data during truck schema upgrade
Upgrading storage for truck retirement SHALL set existing trucks' deletion flags to false and preserve their IDs, names, capacities and availability, along with all collection history and references. If an existing truck violates the new capacity or name constraints, the upgrade SHALL fail with an actionable diagnostic without silently correcting records or publishing a partial upgrade.

#### Scenario: Upgrade existing valid trucks
- **WHEN** initialized collection storage contains valid trucks and historical routes and is upgraded
- **THEN** each existing truck has deleted false and its prior values remain intact
- **AND** all Bins, Routes, RouteStops and ServiceEvents retain their values and references

#### Scenario: Detect incompatible existing records
- **WHEN** an existing truck has capacity above 99 or a blank name at upgrade time
- **THEN** preparation fails identifying the incompatible truck IDs and reason
- **AND** operational values and the previous schema remain unchanged until the operator resolves the incompatibility

#### Scenario: Repeat the upgrade
- **WHEN** schema preparation runs again on already upgraded storage
- **THEN** existing deletion flags and collection records remain unchanged

### Requirement: Unique address identity
Site `site_key` SHALL be unique and non-null. Imported known-address keys SHALL use `address:` followed by the registered address trimmed, whitespace-collapsed, and case-folded. Imported missing-address keys SHALL use `unknown:` followed by VASA external ID. Manual keys SHALL be generated automatically in a separate `manual:` namespace. Display addresses SHALL remain readable. Neither distance nor client addresses SHALL determine imported grouping; manual creation SHALL NOT merge Sites by address.

#### Scenario: Share a site despite different capitalization and distance
- **WHEN** two imported bins have addresses `Kalvarijų g. 10` and `  KALVARIJŲ   g. 10 ` and widely separated coordinates
- **THEN** both reference one site keyed `address:kalvarijų g. 10`

#### Scenario: Keep different addresses separate at identical coordinates
- **WHEN** imported bins at identical coordinates have different normalized registered addresses
- **THEN** they reference different sites

#### Scenario: Enforce uniqueness across reruns and concurrent attempts
- **WHEN** separate import attempts find the same normalized address
- **THEN** storage contains at most one Site for that key

#### Scenario: Isolate missing addresses and fallback-looking real addresses
- **WHEN** imported bins 123 and 456 have missing registered addresses and another has registered address `Unknown address (123)`
- **THEN** their keys are `unknown:123`, `unknown:456`, and `address:unknown address (123)` respectively

#### Scenario: Create a manual Site at an existing address
- **WHEN** a manual creation uses an address already represented in the registry
- **THEN** it receives its own generated `manual:` key and internal Site ID without requiring user key input
- **AND** it does not collide with or replace the existing imported or manual Site

### Requirement: Physical bin source attributes
Physical Bin SHALL persist `site_id`, `external_id`, `inventory_number`, `waste_type`, `capacity_m3`, `latitude`, `longitude`, `object_group`, `waste_carrier`, and `client_count`, in addition to its generated ID and geographical text attributes. Site, waste type and coordinates SHALL remain required. External identity SHALL be nullable, unique when non-NULL, and NULL for manual Bins. Other source attributes SHALL retain their existing nullability; manual create validation SHALL NOT add storage constraints.

#### Scenario: Persist the physical container contract
- **WHEN** a usable VASA bin is imported
- **THEN** inventory number, waste type, unconverted volume, coordinates, group, carrier, and client count retain their source meanings
- **AND** capacity uses NUMERIC, coordinates use DOUBLE PRECISION, client count uses INTEGER, and descriptive attributes use TEXT

#### Scenario: Reject an invalid client count
- **WHEN** a stored client count is negative
- **THEN** storage rejects it

#### Scenario: Store an unknown optional value
- **WHEN** an otherwise usable bin lacks optional source attributes
- **THEN** they can be stored as NULL without fabricating values

#### Scenario: Store several manual Bins without external identity
- **WHEN** multiple valid manual Bins are persisted
- **THEN** each has a generated internal ID and NULL external ID without violating uniqueness
- **AND** unknown client counts remain NULL

#### Scenario: Retain unique known external IDs
- **WHEN** two Bin writes attempt to store the same non-NULL external ID
- **THEN** storage rejects duplication

#### Scenario: Preserve storage's optional source contract
- **WHEN** existing imported records contain NULL optional attributes or an unlisted carrier/waste type
- **THEN** the schema upgrade does not reject, rewrite or restrict those existing records

### Requirement: Bin geographical text attributes
Physical Bin SHALL persist nullable TEXT `district`, `region`, `sub_district`, `city`, `street`, `house_number`, `postal_code`, and `territory_type`. Imported Bins SHALL use their own VASA attributes; manual Bins SHALL use entered or inherited address fields and fixed Vilnius metadata. Postal codes and house numbers SHALL remain text, preserving formatting and leading zeroes. Client-address attributes SHALL NOT replace these bin attributes. Manual form requirements SHALL NOT tighten database nullability.

#### Scenario: Store the supplied bin metadata
- **WHEN** bin 135353 supplies district `Vilniaus m. sav.`, region `Vilniaus apskr.`, sub_district `Verkių sen.`, city `Vilniaus m.`, street `Didlaukio g.`, house_number `53`, postal_code `8303`, and territory_type `Vilniaus m. BA1`
- **THEN** all eight values are stored on that bin under the matching column names

#### Scenario: Preserve a bin postal code independently of its clients
- **WHEN** the bin's postal code is `8303` and a client address has postal code `08303`
- **THEN** the bin stores `8303` without padding it or substituting the client's postal code
- **AND** a bin postal code supplied as `08303` retains its leading zero

#### Scenario: Preserve nonnumeric house numbers
- **WHEN** a bin has house number `53A` or `53-1`
- **THEN** that text is retained without integer conversion

#### Scenario: Persist manual geographical metadata
- **WHEN** a manual Bin is created with no postal code
- **THEN** entered or inherited address fields are stored with NULL postal code, territory type is NULL, and the specified district, region and city are populated

### Requirement: Service snapshots are excluded from bins
Physical Bin SHALL NOT contain `is_serviced`, `service_date`, `last_service_date`, `not_serviced_reason`, `non_serviced_reason`, or `next_service_date` columns. Historical attempts SHALL be represented by BinHist alone; a container detail snapshot SHALL NOT be converted into a fabricated history event.

#### Scenario: Ignore service snapshot fields on a container response
- **WHEN** container metadata includes `is_serviced`, `service_date`, `not_serviced_reason`, and `next_service_date`
- **THEN** no corresponding Bin fields are stored and no history event is manufactured from that snapshot
- **AND** actual historical dates, servicing status, and reasons remain available through the dedicated history import

### Requirement: Derived site coordinates follow membership
Import SHALL recalculate affected Site coordinates from all current distinct member bins whenever it changes their coordinates or membership or refresh removes bins. A Site left without bins by import SHALL be removed. Repeated tile observations SHALL NOT add extra weight to averages. Admin Bin additions/deletions SHALL preserve a surviving Site's stored coordinates; new manual Bins SHALL copy those coordinates.

#### Scenario: Add a bin from a later tile
- **WHEN** a later tile adds another bin sharing an existing site's address
- **THEN** the site's coordinates become the mean across all stored member bins

#### Scenario: Move a bin between sites
- **WHEN** an existing imported bin's registered address changes during import
- **THEN** the bin keeps its identity, both affected site averages are recalculated, and any newly empty old site is removed

#### Scenario: Remove one member from a shared site
- **WHEN** bounded cleanup removes one bin while other members survive, including members outside the bounding box
- **THEN** the site survives with coordinates averaged over all remaining members

#### Scenario: Add a manual member without moving the Site
- **WHEN** an administrator adds a Bin to an existing Site
- **THEN** the new Bin copies stored Site coordinates and Site latitude/longitude remain unchanged

### Requirement: Historical service attempts
BinHist SHALL persist required `bin_id`, timezone-naive `date`, and boolean `was_serviced`, with nullable TEXT `non_serviced_reason` and nullable SMALLINT `fill_level`. Both successful and unsuccessful attempts SHALL be retained. API timestamps SHALL remain TIMESTAMP WITHOUT TIME ZONE without UTC assignment.

#### Scenario: Store an unsuccessful attempt
- **WHEN** VASA supplies an unsuccessful attempt and a non-servicing reason
- **THEN** the timestamp, false status, and supplied reason remain stored

#### Scenario: Preserve naive wall-clock time
- **WHEN** the API supplies `2026-09-01 08:00:00` without an offset
- **THEN** storage retains that wall-clock value without converting it through the database session timezone

### Requirement: Nullable numeric fill observations
BinHist `fill_level` SHALL accept only NULL or the integers 0 through 3. Newly imported VASA attempts SHALL have NULL fill level. Import SHALL NOT infer fill from successful or unsuccessful servicing, and refreshing an existing attempt SHALL preserve a subsequently recorded fill observation.

#### Scenario: Import history without invented fill
- **WHEN** successful and unsuccessful attempts are imported
- **THEN** newly inserted rows both have NULL fill level

#### Scenario: Preserve subsequent observation on refresh
- **WHEN** an existing attempt has fill level 2 and is encountered again
- **THEN** refresh updates source attributes without clearing its fill level

#### Scenario: Reject unsupported fill values
- **WHEN** a history write supplies -1 or 4
- **THEN** storage rejects it

### Requirement: Stable history event identity
The system SHALL enforce one BinHist per `(bin_id, date, was_serviced)` and document that this composite key can collapse distinct attempts with identical timestamp and status. Repeated imports SHALL retain history IDs and update source reasons without producing duplicates.

#### Scenario: Import the same attempt twice
- **WHEN** the same bin, timestamp, and servicing status appear on repeated pages or refreshes
- **THEN** one history row remains with its original generated ID

#### Scenario: Keep distinct statuses at one timestamp
- **WHEN** the same bin has true and false servicing statuses at one timestamp
- **THEN** two history rows remain

### Requirement: Destructive replacement preserves the fleet
The replacement migration SHALL discard old bins, routes, route stops, and service events and create the new collection schema without importing data. All existing trucks and their current identities, names, capacities, availability, and retirement flags SHALL remain unchanged.

#### Scenario: Replace populated old collection storage
- **WHEN** storage containing the old collection tables and trucks is upgraded
- **THEN** obsolete records and tables are removed, new collection tables are empty, and every truck retains its prior values

### Requirement: Generated collection identities
Site, Bin, and BinHist SHALL each have an independently generated BIGINT primary key named `id`. Imported Bins SHALL separately retain their original VASA BIGINT identity in unique non-NULL `external_id`; manual Bins SHALL have NULL external IDs. Truck identities and existing truck records SHALL remain unchanged.

#### Scenario: Generate a history identity independently of its event key
- **WHEN** a valid service attempt is inserted without an internal ID
- **THEN** storage generates its ID independently of bin ID, date, and servicing status

#### Scenario: Generate identities for the other internal records
- **WHEN** a Site and imported physical Bin are inserted without internal IDs
- **THEN** each receives a generated identity and the Bin retains its VASA external ID separately

#### Scenario: Generate a manual Bin identity
- **WHEN** a manual Bin is created without an external ID
- **THEN** storage generates its internal ID without assigning a fake VASA identity

### Requirement: Collection deletion rules
Deleting a Site SHALL cascade to its Bins. Every Bin deletion SHALL cascade to BinHist and resident requests in the same transaction. Admin deletion of a final Bin SHALL also remove its Site; surviving members SHALL preserve Site. Truck soft deletion SHALL retain the truck row and SHALL NOT change sites, bins, bin history, or resident requests. Failed deletion transactions SHALL preserve the affected records together.

#### Scenario: Preserve a referenced site
- **WHEN** an administrator cancels deletion confirmation for a Site with surviving bins
- **THEN** no delete is issued and the Site and its attached bins remain stored

#### Scenario: Delete a referenced site
- **WHEN** direct deletion is requested for a Site with surviving bins
- **THEN** the Site, all its Bins and their history and resident requests are removed together
- **AND** unrelated Sites and their records remain unchanged

#### Scenario: Remove a bin and its history together
- **WHEN** successful bounded refresh cleanup removes a missing imported Bin
- **THEN** that Bin, all its history, and all its resident requests are removed together
- **AND** its Site is removed only if no member bins remain

#### Scenario: Soft delete a truck
- **WHEN** a truck is retired through the management API
- **THEN** its row remains deleted and unavailable and all sites, bins, history, and resident requests remain unchanged

#### Scenario: Cascade a direct bin deletion
- **WHEN** a Bin with resident requests is deleted directly
- **THEN** its resident requests and history are removed in the same transaction without requiring application-side dependent cleanup
- **AND** requests belonging to other surviving bins remain unchanged

#### Scenario: Roll back a bin deletion
- **WHEN** a transaction deleting a Bin and its resident requests fails or is rolled back
- **THEN** the Bin and its requests and history remain stored together

#### Scenario: Remove Site with its final Bin through admin API
- **WHEN** admin deletion removes the final Bin and commits
- **THEN** the Site and Bin are removed together with dependent records

#### Scenario: Roll back cascading Site deletion
- **WHEN** a transaction deleting a Site fails or is rolled back
- **THEN** its Site, Bins, history and resident requests remain stored together

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
- **WHEN** the resident-request upgrade runs against storage at its preceding revision `0009`
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

### Requirement: Data-preserving manual-management schema upgrade
The versioned schema upgrade SHALL allow NULL Bin external IDs and cascading Site-to-Bin deletion while preserving non-NULL external-ID uniqueness. It SHALL preserve all existing records, identities, optional-column nullability, trucks and import checkpoints. It SHALL NOT add carrier/waste restrictions, run an import, reset storage or fabricate records. Repeated schema preparation SHALL preserve data.

#### Scenario: Upgrade populated collection storage
- **WHEN** storage at the preceding revision is upgraded
- **THEN** existing Site/Bin/history/resident-request/truck records and import bookkeeping retain their values and identities
- **AND** the two requested storage changes become effective without new restrictions on optional form fields

#### Scenario: Repeat schema preparation
- **WHEN** startup prepares already upgraded storage
- **THEN** all records remain unchanged and no source import is started

#### Scenario: Reject incompatible downgrade without deleting manual records
- **WHEN** restoring required external IDs is requested while Bins with NULL external IDs exist
- **THEN** downgrade fails with an actionable diagnostic without deleting or modifying those Bins or partially reverting the schema
