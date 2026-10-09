# Spec Delta

## MODIFIED Requirements

### Requirement: Nondeleted truck list and detail
`GET /trucks` SHALL return matching nondeleted trucks in paginated `items`, ordered by ascending ID. `GET /trucks/{id}` SHALL return one nondeleted truck or `404` for a missing or deleted truck. Truck representations SHALL expose exactly `id`, `name`, `max_volume_m3`, `waste_carrier`, `landfill_id` and `available`, with volume as a JSON number. There SHALL be no management option to include deleted trucks.

#### Scenario: List available and unavailable trucks
- **WHEN** the list endpoint is called without filters
- **THEN** both available and unavailable nondeleted trucks are eligible for the requested page, and deleted trucks are excluded from items and total

#### Scenario: Hide deleted detail
- **WHEN** a stored deleted truck's ID is requested through the detail endpoint
- **THEN** the response is `404` without the truck representation

#### Scenario: Read a nondeleted truck
- **WHEN** the detail endpoint is called with a nondeleted truck's ID
- **THEN** the response is `200` with exactly `id`, `name`, `max_volume_m3`, `waste_carrier`, `landfill_id` and `available`, without `max_bins_per_trip` or `deleted`

### Requirement: Combined backend filters
`GET /trucks` SHALL accept optional `name`, `available`, `min_max_volume_m3`, `max_max_volume_m3` and `waste_carrier` query parameters. Name matching SHALL be a case-insensitive literal substring after trimming; blank search SHALL have no effect. Availability SHALL match the requested boolean. Volume bounds SHALL be inclusive. Carrier SHALL match its trimmed value exactly; blank carrier SHALL have no effect. Filters SHALL combine with AND.

#### Scenario: Combine all filters
- **WHEN** the query requests name `vip`, availability true, volume from 18.5 through 35 and carrier `Ecoservice`
- **THEN** only nondeleted available trucks whose names contain `vip` regardless of case, whose maximum volumes are in [18.5, 35] m³ and whose carrier is `Ecoservice` are eligible for items and total

#### Scenario: Search for literal punctuation
- **WHEN** a name search includes `%` or `_`
- **THEN** these characters match literal name characters rather than wildcard expressions

#### Scenario: Apply only an upper bound
- **WHEN** only `max_max_volume_m3=35` is supplied
- **THEN** only otherwise eligible trucks with maximum volume at most 35 m³ contribute to items and total

#### Scenario: Match a carrier literally
- **WHEN** carrier `Ecoservice` is requested and trucks belong to `Ecoservice` and `Ecoservice partner`
- **THEN** only trucks belonging to `Ecoservice` match the carrier filter

### Requirement: Filter validation
The backend SHALL reject malformed availability values, nonnumeric or nonfinite volume bounds, bounds at or below zero and a minimum greater than the maximum with `422`. Positive fractional bounds and values above 99 SHALL be accepted. The frontend SHALL identify invalid bounds in Lithuanian and SHALL NOT request a list using invalid bounds.

#### Scenario: Reject an inverted interval
- **WHEN** the minimum bound is 40 and the maximum is 20
- **THEN** the API returns `422`, or the frontend prevents the request and identifies the invalid interval

#### Scenario: Accept fractional volume bounds
- **WHEN** bounds 0.5 and 120.25 are supplied
- **THEN** the interval is accepted and applied inclusively

#### Scenario: Reject unusable bounds
- **WHEN** a supplied bound is zero, negative, nonnumeric or nonfinite
- **THEN** the API returns `422`, or the frontend prevents the request with a Lithuanian field error

### Requirement: Create truck
`POST /trucks` SHALL require `name`, positive finite numeric `max_volume_m3`, nonempty string `waste_carrier`, an existing positive integer `landfill_id` and explicit boolean `available`. It SHALL generate the ID, set internal `deleted=false`, persist the record and return `201` with the saved representation. The create modal SHALL start with availability true, while allowing the administrator to change it before saving.

#### Scenario: Create a truck from the modal
- **WHEN** an administrator supplies a name, maximum volume 18, carrier `Ecoservice` and landfill 1 and saves without changing the initial availability
- **THEN** the request includes `max_volume_m3=18`, `waste_carrier=Ecoservice`, `landfill_id=1` and `available=true`, and the saved truck has a generated ID and internal `deleted=false`

#### Scenario: Create an unavailable truck
- **WHEN** a valid create request explicitly supplies `available=false`
- **THEN** the saved truck is unavailable and nondeleted

### Requirement: Validate truck mutations
Create and edit SHALL trim names and reject blank names. Supplied volume SHALL be a finite JSON number greater than zero, accepting fractions without the old 99 limit. Carrier SHALL be a trimmed nonempty string; availability SHALL be boolean. Nulls, incorrect types and extra fields SHALL produce `422` without mutation. Duplicate names SHALL be allowed. The frontend SHALL validate name, volume carrier and landfill selection with concise Lithuanian field errors.

#### Scenario: Reject invalid JSON values
- **WHEN** a mutation supplies volume zero, negative, nonfinite, a string or a boolean, or supplies nonboolean availability or a blank/nonstring carrier
- **THEN** the API returns `422` and no truck is created or changed

#### Scenario: Prevent client-controlled deletion flags
- **WHEN** a create or patch body includes `deleted`, `id` or an unknown field
- **THEN** the request is rejected with `422` and stored values remain unchanged

#### Scenario: Trim a duplicate name
- **WHEN** a valid new truck has a name surrounded by spaces that matches another truck after trimming
- **THEN** it is stored with the trimmed name and its own generated ID

#### Scenario: Accept fractional and larger volumes
- **WHEN** otherwise valid mutations supply volumes 0.5, 18.5 or 120
- **THEN** each volume is accepted and returned as a JSON number

#### Scenario: Reject the obsolete field
- **WHEN** a create or patch body includes `max_bins_per_trip`
- **THEN** the API returns `422` without mutation

#### Scenario: Preserve future carrier names through the API
- **WHEN** an otherwise valid request supplies nonempty carrier `Kitas vežėjas`
- **THEN** the API stores and returns that name without enforcing the current UI's four-value list

### Requirement: Edit only nondeleted trucks
`PATCH /trucks/{id}` SHALL accept partial updates to `name`, `max_volume_m3`, `waste_carrier`, `landfill_id` and `available`, preserving omitted values. It SHALL return `200` with the saved representation, or `404` for a missing or deleted truck. An empty patch to a nondeleted truck SHALL return its unchanged representation. Editing SHALL NOT revive a truck retired by a concurrent request.

#### Scenario: Update only availability
- **WHEN** a valid patch contains only `available=false`
- **THEN** availability changes while name, volume, carrier, ID and deletion state are preserved

#### Scenario: Reject editing a retired truck
- **WHEN** an edit is submitted after that truck has been soft deleted
- **THEN** the response is `404` and the truck remains deleted and unavailable

#### Scenario: Update only volume or carrier
- **WHEN** a valid patch supplies only `max_volume_m3` or only `waste_carrier`
- **THEN** only the supplied value changes and the response contains the saved six-field representation

### Requirement: Lithuanian truck screen
Each current-page row SHALL show name, maximum volume with `m³`, carrier, availability and red `Ištrinti` action. Headers SHALL use `Pavadinimas`, `Maksimali talpa`, `Atliekų vežėjas` and `Prieinamumas`. Available SHALL use a green circle with a white checkmark and accessible `Prieinamas` text; unavailable SHALL use a red circle with a white cross and accessible `Neprieinamas` text. Row activation or its accessible name control SHALL open editing.

#### Scenario: Read availability without colour
- **WHEN** an administrator views a row with assistive technology or cannot distinguish its colour
- **THEN** its accessible text identifies availability independently of the icon colour

#### Scenario: Read volume and carrier
- **WHEN** a row represents `Šiukšliavežė 1` with maximum volume 18, carrier `Ecoservice` and availability true
- **THEN** it shows `Šiukšliavežė 1`, `18 m³`, `Ecoservice`, the existing green-circle checkmark and `Ištrinti`

#### Scenario: Read a fractional volume
- **WHEN** a truck has maximum volume 18.5
- **THEN** its row displays `18,5 m³` using Lithuanian number formatting

### Requirement: Truck filter controls
The screen SHALL provide name search, availability choices `Visos`, `Prieinamos`, `Neprieinamos`, optional positive minimum/maximum volume inputs with `m³`, and a carrier select above the list. Valid filter changes SHALL request page 1. Clearing SHALL restore unfiltered nondeleted page 1. Older responses SHALL NOT overwrite newer results.

#### Scenario: Change filters quickly
- **WHEN** a previous search response arrives after the response for the current search
- **THEN** the screen continues displaying results for the current search

#### Scenario: Filter by carrier
- **WHEN** an administrator selects `Biomotorai` while other filters are active
- **THEN** page 1 is requested with that carrier and the other filters, and only matching trucks are displayed

#### Scenario: Clear volume and carrier filters
- **WHEN** an administrator activates `Išvalyti filtrus` with volume/carrier filters active on a later page
- **THEN** all filters and the page input reset, and unfiltered page 1 is requested

### Requirement: Shared create and edit modal
`Pridėti šiukšliavežę` SHALL open the same modal used for row editing. Editing SHALL preload current values. Fields SHALL use `Pavadinimas`, `Maksimali talpa`, `Atliekų vežėjas`, `Sąvartynas` and `Prieinamas`; actions SHALL use `Išsaugoti` and `Atšaukti`. Volume SHALL display a clear `m³` unit and permit decimals. The old site-count field and helper SHALL be removed. Carrier SHALL use a select rather than free text.

#### Scenario: Open a fresh create modal after editing
- **WHEN** an administrator closes an edit modal and opens the add modal
- **THEN** name and volume are blank, no carrier or landfill is selected and availability is true, without values left from the previous truck

#### Scenario: Cancel editing
- **WHEN** an administrator changes modal fields and activates `Atšaukti`
- **THEN** the modal closes without persisting changes

#### Scenario: Load and save current values
- **WHEN** an administrator edits a truck with maximum volume 18.5 and carrier `Ekonovus`
- **THEN** those values are preloaded, the unit is visible, and saving sends numeric `max_volume_m3` and selected `waste_carrier`

### Requirement: Whole-fleet statistics API
`GET /trucks/stats` SHALL return `200` with exactly `{total, available_count, average_max_volume_m3}` over all nondeleted trucks. Total counts the fleet, available_count counts available trucks, and the average is the arithmetic mean of maximum volumes as a JSON number or null for an empty fleet. Table filters and pages SHALL NOT change these statistics.

#### Scenario: Aggregate an eligible fleet
- **WHEN** two nondeleted trucks have maximum volumes 10 and 30, exactly one is available, and a retired truck also exists
- **THEN** statistics return total 2, available_count 1 and average_max_volume_m3 20, excluding the retired truck

#### Scenario: Aggregate an empty fleet
- **WHEN** no nondeleted trucks exist
- **THEN** statistics return total 0, available_count 0 and average_max_volume_m3 null

#### Scenario: Average fractional volumes
- **WHEN** the nondeleted fleet contains maximum volumes 18 and 18.5
- **THEN** statistics return average_max_volume_m3 18.25 without display rounding or the obsolete average field

### Requirement: Fleet overview above the filters
Above the filters/table, the screen SHALL show total trucks, average maximum volume under `Vidutinė maksimali talpa`, and available percentage. The average SHALL display one decimal using Lithuanian number formatting with `m³`. Statistics SHALL cover the entire nondeleted fleet. An empty fleet SHALL show 0 total, — average, 0% available and `0 iš 0`.

#### Scenario: Filter without changing fleet totals
- **WHEN** a table filter reduces the displayed results to one truck
- **THEN** the overview continues showing statistics for all nondeleted trucks

#### Scenario: Display the empty overview
- **WHEN** the statistics response describes an empty fleet
- **THEN** the overview displays 0 trucks, — average and 0% without a division error

#### Scenario: Display average volume
- **WHEN** the fleet's average maximum volume is 18.5
- **THEN** the average card displays `18,5 m³` and contains no site-count terminology

## ADDED Requirements

### Requirement: Numeric volume input
The editor and minimum/maximum volume controls SHALL accept only numeric text when typing or pasting. Nonnumeric input SHALL leave the previous value unchanged. Decimal comma and point SHALL remain supported, and controls SHALL permit clearing and unfinished numeric input during editing. Saving or applying a nonempty bound SHALL still require a positive finite number.

#### Scenario: Reject nonnumeric typing or paste
- **WHEN** an administrator enters or pastes arbitrary letters or mixed text such as `18 m3` into any volume control
- **THEN** that control retains its previous value and no request includes the rejected text

#### Scenario: Edit a decimal volume
- **WHEN** an administrator clears a volume control and enters `18,5` or `18.5`
- **THEN** the control accepts the input and a valid save or filter request uses numeric volume 18.5

### Requirement: Truck carrier selection
The create/edit carrier select SHALL offer exactly `Kauno švara`, `Biomotorai`, `Ecoservice` and `Ekonovus`. Saving through the current UI SHALL require one of these values. The carrier filter SHALL offer these same values plus an unfiltered choice. There SHALL be no free-text carrier entry or automatic carrier discovery.

#### Scenario: Require explicit carrier selection
- **WHEN** an administrator submits a new truck without choosing a carrier
- **THEN** the modal shows `Pasirinkite atliekų vežėją.` beside the select and sends no mutation

#### Scenario: Share carrier options
- **WHEN** an administrator opens the editor carrier select or carrier filter
- **THEN** both contain the four named companies, and the filter also permits all carriers

### Requirement: Display carriers outside the current choices
Truck reads and list rows SHALL preserve carrier names outside the current four UI choices. Editing such a truck SHALL show its stored carrier without silently replacing it, and SHALL require an explicit current-option selection before saving through the modal. Opening or cancelling that modal SHALL cause no mutation.

#### Scenario: Inspect a future carrier
- **WHEN** a stored truck has carrier `Kitas vežėjas` and its row or editor is opened
- **THEN** the original name is visible, no listed carrier is automatically selected, and saving requires an explicit selection of one of the four current options

### Requirement: Read the landfill catalog
`GET /landfills` SHALL return all stored landfills as a JSON array ordered by ID, exposing generated/source IDs, names, separate coordinates, every retained property and collection metadata, without GeoJSON `type` fields. Names and supplied provenance SHALL be returned faithfully. The catalog SHALL have no management write endpoints in this change.

#### Scenario: Load the supplied choices
- **WHEN** the seeded catalog is requested
- **THEN** the response contains all three source facilities in generated-ID order, with missing source fields null and waste streams as arrays

#### Scenario: Read a facility with unknown details
- **WHEN** the catalog contains a named facility with null coordinates, source metadata or other details
- **THEN** the lookup returns those details as null, and its required ID/name remain usable for truck selection

### Requirement: Validate truck landfill assignments
POST SHALL require an existing positive integer `landfill_id`. Supplied PATCH assignments SHALL satisfy the same rule and reject null. Omission SHALL preserve an existing assignment; a nonempty edit of an unassigned truck SHALL require one. `{}` SHALL preserve unchanged values. Invalid assignment SHALL return field-addressable `422` without mutation; missing/deleted Truck behavior SHALL remain `404`.

#### Scenario: Require a valid assignment
- **WHEN** a create request omits landfill, or a mutation supplies null, a numeric string, boolean, fraction, nonpositive or unknown landfill ID
- **THEN** it returns `422` identifying `landfill_id` without changing storage

#### Scenario: Read a transitional truck
- **WHEN** a truck migrated without an assignment is read
- **THEN** its response contains `landfill_id=null` and its original volume/carrier/availability

#### Scenario: Assign an existing unassigned truck
- **WHEN** a nonempty edit of an unassigned truck omits landfill
- **THEN** it returns field-addressable `422` without changing the truck
- **AND** an edit supplying a valid landfill succeeds without replacing omitted fields

#### Scenario: Preserve assignment on a partial edit or retirement
- **WHEN** an assigned truck receives an edit omitting landfill or is retired
- **THEN** its landfill reference is preserved, and retirement still sets deleted true and available false

### Requirement: Choose a landfill in the Truck modal
The existing create/edit modal SHALL use a required `Sąvartynas` dropdown with every stored landfill name and no automatic default. Assigned edits SHALL preload their selection; new/unassigned forms SHALL start blank. Selection SHALL send a numeric ID. Loading, failed or empty catalog states SHALL prevent save with Lithuanian feedback; retry and cancellation SHALL preserve entered values.

#### Scenario: Save a selected facility
- **WHEN** an administrator selects a named landfill and saves a valid form
- **THEN** its generated ID is submitted, persisted and preloaded on reopening the editor

#### Scenario: Require explicit selection
- **WHEN** a form with no landfill selection is submitted
- **THEN** `Pasirinkite sąvartyną.` is shown and no mutation is sent

#### Scenario: Recover from a failed catalog request
- **WHEN** loading choices fails and the administrator retries
- **THEN** other form values are preserved and saving is possible only after valid choices and a selection are available

#### Scenario: Use long names on mobile or with a keyboard
- **WHEN** a landfill is selected at 320px or through keyboard controls
- **THEN** complete names remain readable, controls fit the modal and existing focus/cancel behavior is preserved
