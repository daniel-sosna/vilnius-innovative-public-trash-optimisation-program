# Spec Delta

## MODIFIED Requirements

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

## ADDED Requirements

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
