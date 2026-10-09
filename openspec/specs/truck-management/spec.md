# truck-management Specification

## Purpose

Let administrators maintain the waste-collection fleet through a Lithuanian interface backed by persistent truck records, including filtering, editing and retirement without losing historical attribution.

## Requirements

### Requirement: Role selection and administrator navigation
The system SHALL display `Vairuotojas` and `Administratorius` at `/` without authentication. `Administratorius` SHALL navigate to `/admin/trucks`. `Vairuotojas` SHALL be disabled. Admin screens SHALL share a navigation bar containing `Šiukšliavežės`, linked to `/admin/trucks`. URLs and browser history SHALL reflect navigation.

#### Scenario: Enter truck administration
- **WHEN** a visitor activates `Administratorius` at `/`
- **THEN** the URL becomes `/admin/trucks` and the truck screen and shared admin navigation appear

#### Scenario: Open the truck screen directly
- **WHEN** a visitor opens or refreshes `/admin/trucks`
- **THEN** the truck screen loads at that URL without requiring role selection or authentication

#### Scenario: Navigate back to role selection
- **WHEN** a visitor uses browser Back after entering truck administration from `/`
- **THEN** the role-selection screen returns at `/`

### Requirement: Nondeleted truck list and detail
`GET /trucks` SHALL return matching nondeleted trucks in paginated `items`, ordered by ascending ID. `GET /trucks/{id}` SHALL return one nondeleted truck or `404` for a missing or deleted truck. Truck representations SHALL expose `id`, `name`, `max_bins_per_trip`, `available` and `deleted`. There SHALL be no management option to include deleted trucks.

#### Scenario: List available and unavailable trucks
- **WHEN** the list endpoint is called without filters
- **THEN** both available and unavailable nondeleted trucks are eligible for the requested page, and deleted trucks are excluded from items and total

#### Scenario: Hide deleted detail
- **WHEN** a stored deleted truck's ID is requested through the detail endpoint
- **THEN** the response is `404` without the truck representation

#### Scenario: Read a nondeleted truck
- **WHEN** the detail endpoint is called with a nondeleted truck's ID
- **THEN** the response is `200` with its five fields and `deleted=false`

### Requirement: Combined backend filters
`GET /trucks` SHALL accept optional `name`, `available`, `min_max_bins_per_trip` and `max_max_bins_per_trip` query parameters. Name matching SHALL be a case-insensitive literal substring after trimming the query; blank search SHALL have no effect. Availability SHALL match the requested boolean. Capacity bounds SHALL be inclusive and filters SHALL combine with AND.

#### Scenario: Combine all filters
- **WHEN** the query requests name `vip`, availability true and capacity from 20 through 35
- **THEN** only nondeleted available trucks whose names contain `vip` regardless of case and whose capacities are in [20, 35] are eligible for items and total

#### Scenario: Search for literal punctuation
- **WHEN** a name search includes `%` or `_`
- **THEN** these characters match literal name characters rather than wildcard expressions

#### Scenario: Apply only an upper bound
- **WHEN** only `max_max_bins_per_trip=35` is supplied
- **THEN** only otherwise eligible trucks with capacity at most 35 contribute to items and total

### Requirement: Backend truck pagination
`GET /trucks` SHALL accept a one-based integer `page`, defaulting to 1, with a fixed page size of 10. It SHALL return `{items, total, page, page_size}`, where `page_size` is 10 and `total` counts all filtered nondeleted matches before pagination. Invalid, noninteger or nonpositive pages SHALL return `422`. A valid page beyond the results SHALL return `200` with empty items and the matching total.

#### Scenario: Fetch consecutive pages
- **WHEN** 21 nondeleted trucks match and pages 1, 2 and 3 are requested without intervening changes
- **THEN** the pages contain 10, 10 and 1 trucks respectively in ascending ID order, each reports total 21 and page_size 10, and no truck appears twice

#### Scenario: Paginate filtered matches
- **WHEN** only 5 of 45 stored nondeleted trucks match the filters and page 1 is requested
- **THEN** items contains those 5 trucks and total is 5 rather than 45

#### Scenario: Read beyond the last page
- **WHEN** page 4 is requested with only 21 matching trucks
- **THEN** the response is `200` with items empty, total 21, page 4 and page_size 10

#### Scenario: Reject an invalid page
- **WHEN** the request supplies page 0, a negative page, a fraction or a nonnumeric value
- **THEN** the API returns `422`

### Requirement: Previous and next page controls
The screen SHALL show at most 10 trucks and provide keyboard-operable `Ankstesnis puslapis` and `Kitas puslapis` buttons with a current-page indicator. Previous SHALL be disabled on page 1; next SHALL be disabled on the final page. Both SHALL be disabled while loading, on list failure or when no matches exist. Page changes SHALL preserve filters and fetch the requested backend page without a full page reload.

#### Scenario: Navigate across pages
- **WHEN** 11 trucks match and the administrator activates next on page 1
- **THEN** the second page shows one truck, next is disabled and previous returns to the first page with the same filters

#### Scenario: Show empty pagination
- **WHEN** no trucks match
- **THEN** the screen shows its appropriate empty/no-match state at page 1 with both pagination buttons disabled

### Requirement: Reset and recover the current page
Changing or clearing filters SHALL reset pagination to page 1. After a successful mutation or list refresh, the screen SHALL preserve its current page if valid, otherwise fetch the last remaining page, or page 1 when no matches remain. Responses for obsolete page/filter requests SHALL NOT replace current results or pagination metadata.

#### Scenario: Apply a filter on a later page
- **WHEN** an administrator changes a filter while viewing page 3
- **THEN** the screen requests page 1 with the new filters

#### Scenario: Delete the final truck on the last page
- **WHEN** page 2 has one remaining truck and that truck is deleted, leaving 10 matches
- **THEN** the screen fetches page 1 and displays its 10 trucks rather than an empty page 2

#### Scenario: Ignore an obsolete page response
- **WHEN** a previous page response arrives after a request for a new filter/page combination has completed
- **THEN** the current items, total and page controls remain associated with the new combination

### Requirement: Filter validation
The backend SHALL reject malformed availability values, noninteger capacity bounds, bounds outside 1–99 and a minimum greater than the maximum with `422`. The frontend SHALL identify invalid bounds in Lithuanian and SHALL NOT request a list using invalid bounds.

#### Scenario: Reject an inverted interval
- **WHEN** the minimum bound is 40 and the maximum is 20
- **THEN** the API returns `422`, or the frontend prevents the request and identifies the invalid interval

### Requirement: Create truck
`POST /trucks` SHALL require a name, integer capacity 1–99 and explicit boolean availability. It SHALL generate the ID, set `deleted=false`, persist the record and return `201` with the saved representation. The create modal SHALL start with availability true, while allowing the administrator to change it before saving.

#### Scenario: Create a truck from the modal
- **WHEN** an administrator supplies a name and capacity 35 and saves without changing the initial availability
- **THEN** the request includes `available=true` and the saved truck has a generated ID and `deleted=false`

#### Scenario: Create an unavailable truck
- **WHEN** a valid create request explicitly supplies `available=false`
- **THEN** the saved truck is unavailable and nondeleted

### Requirement: Validate truck mutations
Create and edit SHALL trim names and reject empty or whitespace-only names. Supplied capacity SHALL be an integer 1–99, and supplied availability SHALL be a boolean. Null values, incorrect JSON types and fields outside the permitted input fields SHALL produce `422` without changing records. Duplicate names SHALL be allowed. The frontend SHALL validate name and capacity and show concise Lithuanian field errors.

#### Scenario: Reject invalid JSON values
- **WHEN** a mutation supplies capacity 0, 100, 1.5, a string or a boolean, or supplies nonboolean availability
- **THEN** the API returns `422` and no truck is created or changed

#### Scenario: Prevent client-controlled deletion flags
- **WHEN** a create or patch body includes `deleted`, `id` or an unknown field
- **THEN** the request is rejected with `422` and stored values remain unchanged

#### Scenario: Trim a duplicate name
- **WHEN** a valid new truck has a name surrounded by spaces that matches another truck after trimming
- **THEN** it is stored with the trimmed name and its own generated ID

### Requirement: Edit only nondeleted trucks
`PATCH /trucks/{id}` SHALL accept partial updates to `name`, `max_bins_per_trip` and `available`, preserving omitted values. It SHALL return `200` with the saved representation, or `404` for a missing or deleted truck. An empty patch to a nondeleted truck SHALL return its unchanged representation. Editing SHALL NOT revive a truck retired by a concurrent request.

#### Scenario: Update only availability
- **WHEN** a valid patch contains only `available=false`
- **THEN** availability changes while name, capacity, ID and deletion state are preserved

#### Scenario: Reject editing a retired truck
- **WHEN** an edit is submitted after that truck has been soft deleted
- **THEN** the response is `404` and the truck remains deleted and unavailable

### Requirement: Atomic persistence and failures
Successful mutations SHALL represent committed database changes that survive page reloads and backend restarts. Persistence failure SHALL produce a non-success response without a partial mutation. Unexpected errors SHALL NOT expose database credentials, SQL statements or internal exception details to the UI.

#### Scenario: Fail a mutation
- **WHEN** storage fails during a create, edit or soft delete
- **THEN** the API reports failure and the truck's persistent values are not partially changed

### Requirement: Lithuanian truck screen
The truck screen SHALL show each truck on the current page with its name, `Max Aikštelių per reisą`, availability indicator and red `Ištrinti` action. Available SHALL use a green circle with a white checkmark and accessible `Prieinamas` text; unavailable SHALL use a red circle with a white cross and accessible `Neprieinamas` text. Administrators SHALL be able to open editing by activating a row or its accessible name control.

#### Scenario: Read availability without colour
- **WHEN** an administrator views a row with assistive technology or cannot distinguish its colour
- **THEN** its accessible text identifies availability independently of the icon colour

### Requirement: Truck filter controls
The screen SHALL provide name search, availability choices `Visos`, `Prieinamos`, `Neprieinamos`, and optional minimum/maximum capacity inputs above the list. Changing valid filters SHALL request the first page of the filtered backend list. Clearing filters SHALL restore the first page of the unfiltered nondeleted list. Older responses SHALL NOT overwrite results for newer filters.

#### Scenario: Change filters quickly
- **WHEN** a previous search response arrives after the response for the current search
- **THEN** the screen continues displaying results for the current search

### Requirement: Shared create and edit modal
`Pridėti šiukšliavežę` SHALL open the same modal used for editing from the action row above the table. Editing SHALL preload the current values. Fields SHALL use `Pavadinimas`, `Maksimalus aikštelių skaičius per reisą` and `Prieinamas`; actions SHALL use `Išsaugoti` and `Atšaukti`. The capacity helper SHALL explain `Viena aikštelė gali turėti kelis konteinerius.`

#### Scenario: Open a fresh create modal after editing
- **WHEN** an administrator closes an edit modal and opens the add modal
- **THEN** name and capacity are blank and availability is true, without values left from the previous truck

#### Scenario: Cancel editing
- **WHEN** an administrator changes modal fields and activates `Atšaukti`
- **THEN** the modal closes without persisting changes

### Requirement: Confirm deletion separately from editing
Activating a row's `Ištrinti` SHALL open a confirmation showing `Ar tikrai norite ištrinti šią šiukšliavežę?` with `Atšaukti` and `Ištrinti`. It SHALL NOT also open editing. Cancellation SHALL cause no mutation; confirmation SHALL invoke soft deletion.

#### Scenario: Cancel deletion
- **WHEN** an administrator opens deletion confirmation and activates `Atšaukti`
- **THEN** the truck remains unchanged and no delete request is made

### Requirement: Loading empty and error states
The screen SHALL distinguish loading, an empty unfiltered list, no matches for active filters and API failure using concise Lithuanian messages. Failure SHALL NOT be presented as an empty success. Failed mutations SHALL preserve entered values or deletion context for retry. Successful mutations SHALL refresh the current filtered list without a full page reload; duplicate pending submissions SHALL be prevented.

#### Scenario: Save a truck outside the active filters
- **WHEN** a successful edit makes a truck no longer match the current filters
- **THEN** the modal closes and the refreshed list excludes that truck while keeping the filters

#### Scenario: Retry a failed save
- **WHEN** saving fails because the API is unavailable
- **THEN** the modal remains open with its values, a Lithuanian error toast appears from the top right and retry is permitted after the pending request ends

#### Scenario: Fail list refresh after successful mutation
- **WHEN** a mutation commits but the following list refresh fails
- **THEN** the UI identifies the list-refresh failure and permits retry without claiming that the committed mutation failed

### Requirement: Responsive accessible administration
The screen SHALL remain usable at desktop and 320-pixel viewport widths. Controls SHALL have labels and visible keyboard focus; editing and deletion SHALL be keyboard operable. Dialogs SHALL manage focus and restore it to a logical control on close. The add action SHALL not obscure rows or controls. Styling SHALL use a restrained, consistent hierarchy and spacing.

#### Scenario: Operate on a small screen by keyboard
- **WHEN** an administrator filters, edits and confirms deletion at a 320-pixel viewport using a keyboard
- **THEN** required controls and modal actions remain reachable, labels remain readable and focus moves predictably

### Requirement: Eco branding and neutral page background
The role-selection and admin screens SHALL show a leaf logo beside VipTop branding. The page background SHALL be neutral gray with green accents retained for branding and availability.

#### Scenario: Recognise the eco brand
- **WHEN** a visitor opens role selection or truck administration
- **THEN** VipTop uses the leaf logo and the page background is gray rather than green-tinted

### Requirement: Wider aligned administration layout
At desktop widths, the shared admin content area SHALL widen from approximately 1024 to 1280 pixels. The heading, statistics, filters, action row and table SHALL share its horizontal boundaries. At smaller widths, content SHALL fit the viewport with readable labels and reachable controls.

#### Scenario: Use the wider desktop view
- **WHEN** the truck screen is displayed on a sufficiently wide desktop viewport
- **THEN** its main content uses the wider area and surrounding elements align with the table

#### Scenario: Use the compact view
- **WHEN** the viewport is 320 pixels wide
- **THEN** the content fits without horizontal scrolling and actions remain reachable

### Requirement: Always-visible add and clear actions
The screen SHALL show `Pridėti šiukšliavežę` followed by `Išvalyti filtrus` in a right-aligned action row above the table. Both buttons SHALL have equal width and height and matching text size. Clear SHALL have a visible filled background and remain present without active filters. Clearing SHALL restore unfiltered page 1. Actions SHALL wrap in the same order when needed.

#### Scenario: See actions without active filters
- **WHEN** the list loads with no active filters
- **THEN** both actions are visible in add-then-clear order at the right, and clear has a filled background

#### Scenario: Use equally sized actions
- **WHEN** the action row is displayed on desktop or at 320 pixels
- **THEN** add and clear have equal width and height, with readable labels and usable wrapping

#### Scenario: Clear from a later page
- **WHEN** an administrator activates clear from a filtered or later page
- **THEN** all filters reset and the unfiltered list is requested at page 1

### Requirement: Direct page-number navigation
The pagination controls SHALL include a labeled page-number input and `Eiti` action. Enter or `Eiti` SHALL navigate to a valid integer page from 1 through the last page, preserving filters without reloading. Blank, fractional, nonnumeric or out-of-range input SHALL show a Lithuanian error and issue no page request.

#### Scenario: Jump to a page
- **WHEN** 21 trucks match and an administrator submits page 3
- **THEN** the screen shows the final matching truck at page 3 with the same filters

#### Scenario: Reject an invalid jump
- **WHEN** an administrator submits 0, 1.5, blank text or a page beyond the last page
- **THEN** the current page remains unchanged and a Lithuanian validation message appears

### Requirement: Page input follows current pagination state
The page input SHALL reflect the current page after previous/next navigation, filter reset or page recovery. Page-number submission SHALL be disabled while loading, on list failure, for invalid filters or with no matches. An empty result SHALL settle at page 1.

#### Scenario: Recover after retirement
- **WHEN** deleting the only truck on page 2 leaves 10 matches
- **THEN** the table, indicator and page input all settle at page 1

#### Scenario: Prevent navigation without current data
- **WHEN** the list is loading, failed or has no matches
- **THEN** page-number submission is disabled along with previous/next controls

### Requirement: Whole-fleet statistics API
`GET /trucks/stats` SHALL return `200` with `{total, available_count, average_max_bins_per_trip}` aggregated over all nondeleted trucks. Total counts the fleet, available_count counts available trucks, and the average is the arithmetic mean of their maximum site capacities. Table filters and pages SHALL NOT change these statistics.

#### Scenario: Aggregate an eligible fleet
- **WHEN** two nondeleted trucks have capacities 10 and 30, exactly one is available, and a retired truck also exists
- **THEN** statistics return total 2, available_count 1 and average_max_bins_per_trip 20, excluding the retired truck

#### Scenario: Aggregate an empty fleet
- **WHEN** no nondeleted trucks exist
- **THEN** statistics return total 0, available_count 0 and average_max_bins_per_trip null

### Requirement: Fleet overview above the filters
Above the filters/table, the screen SHALL show total trucks, average maximum site capacity and available percentage. The average SHALL display one decimal using Lithuanian number formatting. Statistics SHALL cover the entire nondeleted fleet. An empty fleet SHALL show 0 total, — average, 0% available and an available/total count of `0 iš 0`.

#### Scenario: Filter without changing fleet totals
- **WHEN** a table filter reduces the displayed results to one truck
- **THEN** the overview continues showing statistics for all nondeleted trucks

#### Scenario: Display the empty overview
- **WHEN** the statistics response describes an empty fleet
- **THEN** the overview displays 0 trucks, — average and 0% without a division error

### Requirement: Consistent overview value typography
Beneath `Prieinamos šiukšliavežės`, the available/total count SHALL use the same font size and weight as the numeric values in the total and average cards. The count and circular indicator SHALL remain readable at desktop and 320 pixels.

#### Scenario: Match overview value typography
- **WHEN** 24 of 27 nondeleted trucks are available
- **THEN** `24 iš 27` appears below the availability title at the same font size and weight as the total and average card values, with the circular indicator still readable at desktop and 320 pixels

### Requirement: Circular availability indicator
The overview SHALL display the available percentage in the centre of a circle with a green arc over a neutral track. The arc SHALL correspond to available_count divided by total; the visible percentage SHALL round to a whole number. Accessible text SHALL identify available trucks independently of colour. An empty fleet SHALL have no green arc.

#### Scenario: Display half the fleet available
- **WHEN** one of two nondeleted trucks is available
- **THEN** the circle displays 50% with a half-circle green arc and accessible availability text

#### Scenario: Display availability endpoints
- **WHEN** the fleet has no available trucks or all its trucks are available
- **THEN** the indicator shows 0% with no green arc or 100% with a complete green arc respectively

### Requirement: Statistics refresh and failure handling
Successful create, edit and retirement SHALL refresh fleet statistics as well as the current filtered page. Statistics SHALL distinguish loading and failure from real zero values and permit retry. A committed mutation followed by a failed statistics refresh SHALL remain identified as successful without encouraging another mutation; a successful save's toast SHALL NOT be replaced with a save-failure toast because a subsequent read failed.

#### Scenario: Refresh after retirement
- **WHEN** an available truck is retired
- **THEN** the refreshed overview excludes it from total, average and available percentage

#### Scenario: Fail an overview refresh
- **WHEN** fetching statistics fails after a successful save
- **THEN** the saved mutation remains successful and the overview shows a Lithuanian refresh error with retry rather than zero statistics

### Requirement: Save result toasts
A committed create or edit SHALL show `Šiukšliavežė išsaugota.` in a success toast entering from the top right, replacing inline save-success text. Failed create or edit requests SHALL show concise Lithuanian error toasts in the same position while preserving the open modal and entered values. Field validation SHALL remain beside the relevant inputs.

#### Scenario: Save successfully
- **WHEN** a create or edit request commits successfully
- **THEN** its dialog closes, a success toast appears from the top right, no inline save-success text is rendered and the current list and overview refresh

#### Scenario: Save fails
- **WHEN** a create or edit request fails
- **THEN** an error toast appears from the top right above the open dialog, entered values remain available and retry is possible after the request ends

#### Scenario: Keep validation beside fields
- **WHEN** an administrator submits an invalid name or capacity
- **THEN** the relevant input retains its Lithuanian field error, regardless of toast feedback

#### Scenario: Refresh fails after committed save
- **WHEN** a create or edit commits and its subsequent list or statistics refresh fails
- **THEN** the save remains successful, the failed read shows its own error and retry control, and retry does not repeat the mutation or its success toast

### Requirement: Accessible responsive toasts
Save toasts SHALL support labeled dismissal and accessible announcements without taking focus. They SHALL remain visible above open dialogs, fit a 320-pixel viewport and respect reduced-motion preferences.

#### Scenario: Receive feedback while editing on mobile
- **WHEN** a failed save produces a toast above an open editor at 320 pixels
- **THEN** its message and dismissal control fit the viewport, its announcement identifies the failure and editing focus remains unchanged

#### Scenario: Receive feedback with reduced motion
- **WHEN** a save toast appears with reduced motion enabled
- **THEN** it remains readable and dismissible without the corner-entry motion

### Requirement: Mobile administrator navigation
Below 640 pixels, admin navbar links SHALL be collapsed into a hamburger menu, closed initially, with a labeled keyboard-operable toggle exposing its expanded state. Opening it SHALL reveal the existing navigation links. Selecting a link or pressing Escape SHALL close it; Escape SHALL restore focus to the toggle. At widths of 640 pixels or more, the links SHALL be visible in the navbar without the hamburger toggle. Branding SHALL remain visible and navigation SHALL fit a 320-pixel viewport.

#### Scenario: Open and use mobile navigation
- **WHEN** an administrator opens the hamburger menu at 320 pixels and activates `Šiukšliavežės`
- **THEN** the menu reveals that link, navigation reaches `/admin/trucks` and the menu closes

#### Scenario: Close mobile navigation by keyboard
- **WHEN** the mobile menu is open and the administrator presses Escape
- **THEN** the menu closes and focus returns to its toggle

#### Scenario: Show desktop navigation
- **WHEN** the viewport is at least 640 pixels wide
- **THEN** the navbar links are visible directly and the hamburger toggle is hidden

### Requirement: Fleet retirement API
`DELETE /trucks/{id}` SHALL set `deleted=true` and `available=false` together for a nondeleted truck, return `204` without a body, and retain the row. A missing or already deleted ID SHALL return `404`. Management operations SHALL NOT physically delete trucks or restore them. Retirement SHALL NOT modify sites, physical bins, or bin history.

#### Scenario: Retire a truck independently of collection data
- **WHEN** a nondeleted truck is deleted through the API while sites, bins, and history exist
- **THEN** its row remains with deleted true and available false and all collection data retains its values and references

#### Scenario: Repeat a deletion
- **WHEN** deletion is requested again for an already deleted truck
- **THEN** the response is `404` and the retained record remains unchanged
