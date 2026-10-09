# Spec Delta

## MODIFIED Requirements

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

## ADDED Requirements

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
Storage SHALL reject deleting a Site that still has bins. Removing a Bin during successful bounded refresh cleanup SHALL also remove its BinHist records. Truck soft deletion SHALL retain the truck row and SHALL NOT change sites, bins, or bin history.

#### Scenario: Preserve a referenced site
- **WHEN** direct deletion is requested for a Site with surviving bins
- **THEN** deletion is rejected and its bins remain attached

#### Scenario: Remove a bin and its history together
- **WHEN** successful bounded refresh cleanup removes a missing Bin
- **THEN** that Bin and all its history are removed together
- **AND** its Site is removed only if no member bins remain

#### Scenario: Soft delete a truck
- **WHEN** a truck is retired through the management API
- **THEN** its row remains deleted and unavailable and all sites, bins, and history remain unchanged

## REMOVED Requirements

### Requirement: Daily route records
**Reason**: Route storage is deliberately removed from this data replacement.
**Migration**: Drop `routes` after its dependents; do not transfer existing route records.

### Requirement: Ordered route stop records
**Reason**: No route execution or optimisation is included in this change.
**Migration**: Drop `route_stops` and remove dependent runtime code.

### Requirement: Raw service observation records
**Reason**: Route-linked complete site emptying is replaced by physical-bin service attempts.
**Migration**: Drop `service_events` without transferring data; retrieve attempts manually from VASA into `bin_hist`.

### Requirement: Categorical fill observations
**Reason**: The new history contract uses nullable numeric observations instead of mandatory text categories.
**Migration**: Discard old event categories; leave newly imported fill levels NULL.

### Requirement: Derive service truck attribution through the route
**Reason**: VASA history does not supply route or truck attribution and route storage is removed.
**Migration**: Remove route-based joins and dependent current documentation.

### Requirement: Optional site metadata text
**Reason**: GIS `type` and `greening` are not fields of the new site/container model.
**Migration**: Drop old bins and discontinue the GIS metadata mappings.

### Requirement: Independent generated record identities
**Reason**: Route and event identities are replaced by independent Site, physical Bin, and BinHist identities.
**Migration**: Retain Truck identities; generate new BIGINT collection identities and retain VASA external IDs separately.

### Requirement: Protect referenced collection records
**Reason**: Old route-reference restrictions are obsolete and bounded refresh deliberately removes a missing bin and its history.
**Migration**: Restrict Site deletion while bins remain; remove BinHist with its Bin and preserve fleet retirement behavior.
