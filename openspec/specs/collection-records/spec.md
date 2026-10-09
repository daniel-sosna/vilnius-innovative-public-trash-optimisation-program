# collection-records Specification

## Purpose

Provide persistent collection-site, truck, route, stop, and service-observation records that future collection workflows and analytical consumers can use without duplicating operational facts.

## Requirements

### Requirement: Collection site records
The system SHALL persist Site records with `id`, `site_key`, `address`, `latitude`, and `longitude`, all required. A site SHALL group bins by normalized registered address only. Its coordinates SHALL be the arithmetic mean of all currently assigned bins, with latitude in [-90, 90] and longitude in [-180, 180]. They SHALL be described as derived averages, not surveyed physical collection points.

#### Scenario: Persist a collection site
- **WHEN** physical bins with one registered address are persisted
- **THEN** they reference one generated Site identity with a readable address and their mean coordinates

#### Scenario: Reject unusable stored coordinates
- **WHEN** a Site or Bin write supplies a missing, nonfinite, or geographically out-of-range coordinate
- **THEN** storage rejects the write without publishing its transaction

#### Scenario: Preserve a site without an address
- **WHEN** a bin has no registered address
- **THEN** its site has a readable fallback address and a deterministic key based on that bin's external ID
- **AND** it does not share a site with other unknown-address bins

### Requirement: Truck records
The system SHALL persist Truck records with only `id`, `name`, `max_bins_per_trip`, `available` and `deleted`, all required. Name SHALL be nonempty after trimming. Capacity SHALL be an integer 1–99 counting collection sites per trip. Availability SHALL be a boolean that future route generation can consume. Deletion SHALL be a boolean defaulting to false. A deleted truck SHALL always be unavailable.

#### Scenario: Persist truck capacity and availability
- **WHEN** a truck named "Truck 3" is stored with capacity 35 and availability true
- **THEN** the stored truck exposes a capacity of 35 sites per trip and availability true

#### Scenario: Reject unusable truck capacity
- **WHEN** a truck write supplies zero, a negative value, or a missing value for capacity
- **THEN** the write is rejected

#### Scenario: Enforce the upper capacity bound
- **WHEN** a truck write supplies capacity greater than 99
- **THEN** the write is rejected without changing the truck's existing values

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
Site `site_key` SHALL be unique and non-null. Known-address keys SHALL use `address:` followed by the registered address trimmed, whitespace-collapsed, and case-folded. Missing-address keys SHALL use `unknown:` followed by VASA external ID. Display addresses SHALL remain readable. Neither distance nor client addresses SHALL determine grouping.

#### Scenario: Share a site despite different capitalization and distance
- **WHEN** two bins have addresses `Kalvarijų g. 10` and `  KALVARIJŲ   g. 10 ` and widely separated coordinates
- **THEN** both reference one site keyed `address:kalvarijų g. 10`

#### Scenario: Keep different addresses separate at identical coordinates
- **WHEN** bins at identical coordinates have different normalized registered addresses
- **THEN** they reference different sites

#### Scenario: Enforce uniqueness across reruns and concurrent attempts
- **WHEN** separate import attempts find the same normalized address
- **THEN** storage contains at most one Site for that key

#### Scenario: Isolate missing addresses and fallback-looking real addresses
- **WHEN** bins 123 and 456 have missing registered addresses and another has registered address `Unknown address (123)`
- **THEN** their keys are `unknown:123`, `unknown:456`, and `address:unknown address (123)` respectively

### Requirement: Physical bin source attributes
Physical Bin SHALL persist `site_id`, `external_id`, `inventory_number`, `waste_type`, `capacity_m3`, `latitude`, `longitude`, `object_group`, `waste_carrier`, and `client_count`, in addition to its generated ID and the geographical text attributes defined below. Site, external identity, waste type, and coordinates SHALL be required; other source attributes SHALL be nullable.

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

### Requirement: Bin geographical text attributes
Physical Bin SHALL additionally persist nullable TEXT `district`, `region`, `sub_district`, `city`, `street`, `house_number`, `postal_code`, and `territory_type` from its own VASA attributes. Postal codes and house numbers SHALL remain text, preserving supplied formatting and leading zeroes. Client-address attributes SHALL NOT replace these bin attributes.

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

### Requirement: Service snapshots are excluded from bins
Physical Bin SHALL NOT contain `is_serviced`, `service_date`, `last_service_date`, `not_serviced_reason`, `non_serviced_reason`, or `next_service_date` columns. Historical attempts SHALL be represented by BinHist alone; a container detail snapshot SHALL NOT be converted into a fabricated history event.

#### Scenario: Ignore service snapshot fields on a container response
- **WHEN** container metadata includes `is_serviced`, `service_date`, `not_serviced_reason`, and `next_service_date`
- **THEN** no corresponding Bin fields are stored and no history event is manufactured from that snapshot
- **AND** actual historical dates, servicing status, and reasons remain available through the dedicated history import

### Requirement: Derived site coordinates follow membership
A Site's coordinates SHALL be recalculated from all current distinct member bins whenever import changes their coordinates or membership or refresh removes bins. A Site left without bins SHALL be removed. Repeated tile observations SHALL NOT add extra weight to the averages.

#### Scenario: Add a bin from a later tile
- **WHEN** a later tile adds another bin sharing an existing site's address
- **THEN** the site's coordinates become the mean across all stored member bins

#### Scenario: Move a bin between sites
- **WHEN** an existing bin's registered address changes
- **THEN** the bin keeps its identity, both affected site averages are recalculated, and any newly empty old site is removed

#### Scenario: Remove one member from a shared site
- **WHEN** bounded cleanup removes one bin while other members survive, including members outside the bounding box
- **THEN** the site survives with coordinates averaged over all remaining members

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
Site, Bin, and BinHist SHALL each have an independently generated BIGINT primary key named `id`. Bin SHALL separately retain its original VASA BIGINT identity as unique, required `external_id`. Truck identities and existing truck records SHALL remain unchanged.

#### Scenario: Generate a history identity independently of its event key
- **WHEN** a valid service attempt is inserted without an internal ID
- **THEN** storage generates its ID independently of bin ID, date, and servicing status

#### Scenario: Generate identities for the other internal records
- **WHEN** a Site and physical Bin are inserted without internal IDs
- **THEN** each receives a generated identity and the Bin retains its VASA external ID separately

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
