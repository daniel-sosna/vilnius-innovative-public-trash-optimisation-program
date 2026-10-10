# collection-site-management Specification

## Purpose

Allow administrators to maintain collection Sites and Bins through manual creation and confirmed hard deletion while preserving the existing registry browsing experience.

## Requirements

### Requirement: Site creation entry and initial containers
At `/admin/sites`, the UI SHALL show a right-aligned `Pridėti surinkimo vietą` button on the address-search/clear row (wrapping on narrow screens) opening a modal with address inputs, an interactive location map, Bin forms and create/cancel actions. The modal SHALL start with one Bin form, allow adding/removing forms, and prevent removal of the final form. Creation SHALL require at least one Bin.

#### Scenario: Prepare several initial containers
- **WHEN** an administrator opens creation and adds two Bin forms
- **THEN** three independently editable Bin forms are available
- **AND** forms can be removed until exactly one remains

#### Scenario: Cancel creation
- **WHEN** an administrator cancels before submission
- **THEN** no Site or Bin is persisted

### Requirement: Required address input and optional postal code
New-Site forms and `POST /sites` SHALL require nonblank `street`, `sub_district` and `house_number`. `postal_code` SHALL be optional, with omitted, NULL or blank values stored as NULL. Text SHALL be trimmed without numeric coercion of house numbers or postal codes. Site `address` SHALL use `street house_number, sub_district` followed by `, postal_code` when present.

#### Scenario: Create without a postal code
- **WHEN** street is `Didlaukio g.`, house number is `53A`, sub-district is `Verkių sen.` and postal code is empty
- **THEN** the Site address is `Didlaukio g. 53A, Verkių sen.`
- **AND** its initial Bins store those address fields with NULL postal codes

#### Scenario: Preserve postal formatting
- **WHEN** the same address is submitted with postal code `08303`
- **THEN** the Site address ends in `, 08303` and each initial Bin retains postal code `08303`

#### Scenario: Reject a missing required address value
- **WHEN** street, sub-district or house number is absent, NULL, empty or whitespace-only
- **THEN** the form identifies the invalid field and the create API rejects the request with 422 without persisting records

### Requirement: Explicit location selection for new Sites
The creation map SHALL use configured `VITE_MAP_STYLE_URL`, initially `https://tiles.openfreemap.org/styles/liberty`, and allow pan, zoom and location selection by click. Selection SHALL set Site latitude/longitude and show or move one marker. Initial map centering SHALL NOT count as selection. Creation SHALL require finite coordinates in their valid geographical ranges. Enter/Space on the focused map SHALL select its center.

#### Scenario: Select and replace a location
- **WHEN** an administrator clicks two different map locations before submission
- **THEN** one marker appears at the second location and the submitted coordinates match that location without swapping latitude and longitude
- **AND** every initial Bin receives those exact Site coordinates

#### Scenario: Submit before selecting a location
- **WHEN** no map location has been selected
- **THEN** the form prevents creation
- **AND** the API rejects absent, nonfinite or out-of-range coordinates with 422

#### Scenario: Map resources fail before selection
- **WHEN** the configured map cannot load
- **THEN** a Lithuanian error/retry state is shown, entered form values remain available, and creation remains blocked until location selection is possible

### Requirement: Creation location presentation
The map SHALL have the title `Spauskite ant žemėlapio, kad pasirinktumėte lokaciją`. Latitude/longitude SHALL appear as disabled, nonselectable fields immediately below the map, initially empty. Selection SHALL update both. No other selection text, coordinate status or selection buttons SHALL appear below the map.

#### Scenario: Inspect a selected location
- **WHEN** an administrator selects a point on the creation map
- **THEN** the disabled latitude/longitude fields show that point and one marker appears
- **AND** the coordinate inputs cannot receive focus, be edited or have their text selected

#### Scenario: Select by keyboard
- **WHEN** an administrator pans the focused map with arrow keys and presses Enter or Space
- **THEN** the current map center is selected without submitting the form

### Requirement: Required manual Bin definitions
Both creation forms and create APIs SHALL require `object_group`, `capacity_m3`, `waste_carrier`, `inventory_number` and `waste_type` for every manual Bin. Descriptive values SHALL be nonblank after trimming. Required inputs SHALL NOT tighten existing database nullability or alter previously stored optional values. `Naudotojai` SHALL map to descriptive `object_group`, not a numeric client count.

#### Scenario: Reject an incomplete Bin definition
- **WHEN** a Bin's user group, capacity, carrier, inventory number or waste type is omitted, NULL or empty
- **THEN** the form identifies that Bin's invalid input and the create API returns 422 without persisting any part of the request

#### Scenario: Keep existing nullable records browsable
- **WHEN** imported Bins contain NULL inventory numbers, capacities, groups or carriers
- **THEN** the new creation rules do not change those stored values or their `N/A` presentation

### Requirement: Positive numeric manual capacity
Manual `capacity_m3` SHALL be a positive finite number in m³, supporting decimal values without a fixed upper bound. The form and create APIs SHALL reject blank, nonnumeric, boolean, zero, negative and nonfinite values. API capacity input SHALL be a JSON number; display rounding SHALL NOT round the persisted value.

#### Scenario: Accept decimal capacity
- **WHEN** a valid Bin definition supplies numeric capacity `1.1`
- **THEN** creation stores capacity 1.1 and existing capacity aggregates include it

#### Scenario: Reject invalid capacity
- **WHEN** capacity is missing, blank, `abc`, `1.1abc`, a string instead of a JSON number, true, zero, negative, NaN or infinity
- **THEN** creation is rejected without persisted Site/Bin records

### Requirement: Manual carrier and waste selections
Carrier dropdowns SHALL offer `Kauno švara`, `Biomotorai`, `Ecoservice` and `Ekonovus`. Waste dropdowns SHALL offer the three existing Lithuanian categories and submit their existing stored values. Create APIs SHALL accept only these selections. Storage SHALL remain unrestricted by new carrier/waste constraints, preserving other existing source values.

#### Scenario: Map Lithuanian waste selections
- **WHEN** an administrator selects `Mišrios komunalinės atliekos`, `Popieriaus ir plastiko atliekos` or `Stiklo atliekos`
- **THEN** the created Bin stores `Mixed municipal waste`, `Paper/plastic waste` or `Glass waste`, respectively

#### Scenario: Require a permitted selection
- **WHEN** a create request supplies an unlisted carrier or waste type
- **THEN** the API returns 422 without persisting the request
- **AND** already stored unlisted values remain unchanged and readable

### Requirement: Backend-assigned manual Bin metadata
Every manual Bin SHALL receive `external_id = NULL`, `territory_type = NULL`, `district = "Vilniaus m. sav."`, `region = "Vilniaus apskr."` and `city = "Vilniaus m."`. Site membership, coordinates and inherited address metadata SHALL be assigned by the backend. Creation SHALL leave `client_count` NULL and SHALL NOT fabricate history, resident requests or fill observations.

#### Scenario: Create independent manual containers
- **WHEN** two valid manual Bins are created
- **THEN** they receive separate internal IDs and NULL external IDs, with the fixed metadata and their respective Site's coordinates
- **AND** no client count or history is inferred from the supplied user group

#### Scenario: Reject attempts to override assigned fields
- **WHEN** a create request includes Bin external identity, Site membership, coordinates or geographical metadata beyond its permitted input fields
- **THEN** the API returns 422 and does not persist caller-assigned metadata

### Requirement: Atomic Site and initial Bin creation API
`POST /sites` SHALL accept address fields, latitude, longitude and one or more Bin definitions. It SHALL persist the Site and all initial Bins together and return 201 with the created Site summary only after commit. Empty Bin lists SHALL return 422. Persistence failures SHALL leave no partial Site/Bin records.

#### Scenario: Commit a complete Site
- **WHEN** a valid request contains two initial Bins
- **THEN** one Site and both Bins are persisted together and the response supplies Site `id`, `address` and `bin_count = 2`
- **AND** the UI closes the modal, returns to `/admin/sites` and refreshes the list and overview without a full page reload

#### Scenario: Fail during initial Bin creation
- **WHEN** saving any initial Bin or committing the transaction fails
- **THEN** neither the Site nor any initial Bin remains committed
- **AND** the UI retains entered values and shows a Lithuanian failure state

#### Scenario: Reject zero initial Bins
- **WHEN** `POST /sites` receives an empty Bin list
- **THEN** it returns 422 and creates no Site

### Requirement: Add one Bin under an existing Site
At `/admin/sites/{id}`, `Pridėti konteinerį` SHALL appear at the top right above the Bin list and open a modal containing only the five Bin inputs. `POST /sites/{site_id}/bins` SHALL create one Bin and return 201 with its Bin summary after commit. The backend SHALL inherit coordinates from Site and all four address values from the lowest-ID child, preserving NULLs; with no child those address values SHALL be NULL.

#### Scenario: Add to an imported Site
- **WHEN** the lowest-ID child has NULL postal code while another child has a known postal code
- **THEN** the new Bin inherits NULL postal code and all other address fields from the same lowest-ID child
- **AND** its coordinates match Site coordinates and no existing Site/Bin value is changed

#### Scenario: Add to a legacy empty Site
- **WHEN** an existing Site has zero Bins and a valid Bin definition is submitted
- **THEN** the new Bin receives the Site's coordinates and NULL inherited address fields without parsing the Site display address

#### Scenario: Refresh after adding a Bin
- **WHEN** Bin creation succeeds
- **THEN** the modal closes and the Site's Bin list and statistics update without a full page reload
- **AND** an administrator can inspect the new Bin using normal pagination and history browsing

### Requirement: Confirmed Site deletion
Every Site list item SHALL have the same small ghost-style red `Ištrinti` action as Truck rows that opens confirmation without navigating to Site details. Cancel SHALL preserve records. Confirm SHALL invoke `DELETE /sites/{site_id}`, hard-delete Site and dependent Bins/history/resident requests atomically, and return 204 after commit. Failed deletion SHALL preserve the records and show a Lithuanian recoverable error.

#### Scenario: Delete a Site with multiple Bins
- **WHEN** an administrator confirms deleting a listed Site with three Bins
- **THEN** that Site, its three Bins and their dependent history/resident requests are removed together
- **AND** the Site disappears from the list and the global overview updates without a full page reload

#### Scenario: Cancel without navigating
- **WHEN** an administrator activates a Site's delete action and then cancels
- **THEN** the route and Site records remain unchanged

### Requirement: Confirmed Bin deletion and final-child outcome
Every Bin list item SHALL have the same small ghost-style red `Ištrinti` action as Truck rows opening confirmation independently of its history dialog. `DELETE /bins/{bin_id}` SHALL delete Bin and dependent history/resident requests atomically, preserving Site if other Bins remain and deleting Site otherwise. It SHALL return 200 with `site_id` and `site_deleted` after commit. The backend SHALL determine the outcome across all children, not just the visible page.

#### Scenario: Delete one of several Bins
- **WHEN** a confirmed deletion removes one Bin and other Bins remain, including on another page
- **THEN** the response has `site_deleted = false`, Site coordinates remain unchanged, and its Bin list and statistics refresh without a full page reload

#### Scenario: Delete the final Bin
- **WHEN** the confirmed deletion removes the last Bin
- **THEN** Bin, history, resident requests and Site are removed in the same transaction
- **AND** the response has `site_deleted = true` and the UI redirects to `/admin/sites`

#### Scenario: Fail during final-child deletion
- **WHEN** the deletion transaction fails before commit
- **THEN** Site, Bin and dependent records remain together and the UI does not redirect as though deletion succeeded

### Requirement: Concurrent child mutations preserve Site consistency
Concurrent admin additions and deletions under the same Site SHALL resolve to a committed sequence in which the Site exists exactly when surviving Bins require it. Deleting its last Bins SHALL NOT leave an empty Site through competing deletion requests. A Bin addition SHALL NOT report success under a deleted Site.

#### Scenario: Delete two final children concurrently
- **WHEN** two requests concurrently delete the only two Bins of a Site
- **THEN** successful commits remove both Bins and their Site without leaving detached records or an empty Site

#### Scenario: Add a Bin while deleting the last child
- **WHEN** an addition competes with final-Bin deletion
- **THEN** either the added Bin commits first and the Site survives, or deletion commits first and the addition reports a missing Site

### Requirement: Missing mutation targets and failure responses
New mutation endpoints SHALL return 404 for missing positive Site/Bin IDs, including positive IDs beyond storage's identity range, and 422 for nonpositive or noninteger IDs or invalid create bodies. Failures SHALL expose no database diagnostics to users. Missing records discovered during a UI mutation SHALL offer recovery through refreshed data or return to the Site list.

#### Scenario: Add under a missing Site
- **WHEN** the selected Site is removed before Bin creation
- **THEN** the API returns 404 and creates no Bin
- **AND** the modal shows a Lithuanian missing-Site state with navigation back to the list

#### Scenario: Delete a missing record
- **WHEN** Site or Bin deletion targets a record already removed
- **THEN** the API returns 404 and the UI can refresh its current data without claiming a newly committed deletion

### Requirement: Mutation refresh respects pagination and current selection
Successful management actions SHALL refresh affected lists and aggregates, retain applicable address filters, and recover to the last valid page when deletion empties a page. Late reads from before a mutation or prior selection SHALL NOT replace refreshed data. Unrelated surviving histories and records SHALL remain available.

#### Scenario: Delete the only Site on the final page
- **WHEN** deletion makes the current Site page exceed the remaining page count
- **THEN** the UI retrieves the last valid page under its current filter and updates overview statistics

#### Scenario: Ignore an obsolete Bin list response
- **WHEN** a pre-deletion Bin-list request completes after the refreshed list
- **THEN** it does not restore the deleted Bin in the displayed list

### Requirement: Lithuanian accessible and recoverable management dialogs
Management dialogs SHALL follow the existing admin visual language, use Lithuanian application text and remain usable at 320px width. The Site modal SHALL scroll within the viewport. Controls SHALL support keyboard operation, accessible errors and focus restoration; location selection SHALL have a keyboard-accessible equivalent. Pending submissions SHALL prevent duplicate requests. Editable fields SHALL use empty inputs, never `N/A` as a placeholder value.

#### Scenario: Use creation on a narrow screen
- **WHEN** an administrator opens creation at 320px width with several Bin forms
- **THEN** map, inputs and create/cancel controls remain reachable without horizontal page overflow

#### Scenario: Operate creation by keyboard
- **WHEN** an administrator uses only the keyboard
- **THEN** inputs, map panning/zooming, location selection and submission are operable
- **AND** canceling returns focus to the originating control

#### Scenario: Prevent duplicate pending submissions
- **WHEN** an administrator repeatedly activates create or confirm while a request is pending
- **THEN** only one mutation is sent for that pending interaction
- **AND** a failed request retains relevant form values and permits an explicit retry without automatic POST replay
