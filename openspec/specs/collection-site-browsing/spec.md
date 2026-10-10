# collection-site-browsing Specification

## Purpose

Allow administrators to browse imported collection sites, inspect their locations and containers, and understand recorded container service attempts without changing operational data or interrupting import.

## Requirements

### Requirement: Collection browsing preserves operational data and import
Collection GET requests SHALL remain read-only and preserve stored operational data and import progress. Explicit management actions SHALL create/delete records only under the collection-site-management contract. The required manual-management migration SHALL preserve existing data and PostgreSQL storage. Browsing, management and application startup SHALL NOT invoke import or reset tables; an independently invoked importer SHALL remain independent.

#### Scenario: Browse during import
- **WHEN** an administrator requests sites, statistics, bins or history while import is progressing
- **THEN** the feature reads committed records without modifying data, schema or import progress
- **AND** the importer continues independently

#### Scenario: Activate after completed import
- **WHEN** the completed one-time import is followed by activation of collection management through the real Compose setup
- **THEN** the required migration and rebuilt application preserve existing records and database storage
- **AND** no automatic import or table reset occurs

#### Scenario: Start separate verification servers
- **WHEN** separate frontend/backend servers are started for browsing verification
- **THEN** verification GET requests do not mutate the registry or import checkpoints
- **AND** startup performs no import or storage reset

#### Scenario: Browse after a manual mutation
- **WHEN** an administrator explicitly creates or deletes collection records and then requests the list, details or statistics
- **THEN** the reads reflect committed records without themselves creating, deleting or editing data

### Requirement: Admin collection navigation
The admin navbar SHALL include `Šiukšlių surinkimo vietos`, opening `/admin/sites`. A site SHALL open at `/admin/sites/{id}`. Navigation SHALL follow the existing responsive admin behavior and remain usable by keyboard and touch.

#### Scenario: Open a site through the admin navbar
- **WHEN** the administrator selects `Šiukšlių surinkimo vietos` and then a site row
- **THEN** the site list and the selected site's details open at their corresponding routes
- **AND** the navbar identifies collection browsing as active on both routes

#### Scenario: Open a detail URL directly
- **WHEN** a user opens or refreshes `/admin/sites/{id}` directly
- **THEN** the application retrieves and displays that site's details independently of prior list navigation

### Requirement: Backend-paginated site browsing
`GET /sites` SHALL accept `page`, `page_size` and optional `address`, defaulting to page 1 and size 15. It SHALL return `items` containing `id`, `address`, `bin_count`, plus `total`, `page` and `page_size`. It SHALL paginate in the backend without first loading the entire registry. The UI SHALL show address and bin count, omit `site_key`, and reuse existing pagination controls.

#### Scenario: Read the second site page
- **WHEN** 31 sites exist and page 2 is requested with default size
- **THEN** the API returns 15 sites, total 31, page 2 and page size 15
- **AND** stable ascending site-ID order determines page membership for unchanged data

#### Scenario: Follow a site row
- **WHEN** a user hovers or keyboard-focuses a site row
- **THEN** an external-link-style icon appears at its end
- **AND** activating the row opens its detail route in the same tab

### Requirement: Literal address filtering
Site address filtering SHALL use a trimmed, case-insensitive partial match in the backend. Blank search SHALL apply no filter, and `%` and `_` SHALL be treated as literal characters. Filter changes SHALL reset the UI to page 1. Returned totals SHALL cover the same filtered set as the page.

#### Scenario: Search part of a Lithuanian address
- **WHEN** a user changes the address search from page 3 to a case variant of part of a stored address
- **THEN** matching sites are requested on page 1
- **AND** the pagination total reflects all matches rather than only the displayed page

#### Scenario: Distinguish no matches from an empty registry
- **WHEN** a nonblank address filter matches no sites
- **THEN** the UI shows a Lithuanian no-matches state with an option to clear the filter
- **AND** an empty unfiltered registry has its own empty-list message

### Requirement: Pagination validation and missing parents
Pages and page sizes SHALL be positive integers. Site/bin page sizes SHALL be at most 100; history page size SHALL be at most 20. Invalid parameters SHALL return 422. A valid page beyond available results SHALL return empty items and the matching total. Missing site details, missing site parents for bin lists, and missing bin parents for history SHALL return 404.

#### Scenario: Reject oversized history retrieval
- **WHEN** a caller requests history with page size 21, page 0, or a noninteger page
- **THEN** the API returns 422 without returning a history page

#### Scenario: Request a page beyond the results
- **WHEN** an existing parent's requested page exceeds its result set
- **THEN** the API returns empty items with that parent's correct total and requested pagination metadata
- **AND** any history percentages still cover all of its history

#### Scenario: Request a nonexistent parent
- **WHEN** a positive site or bin ID does not exist for the requested endpoint
- **THEN** the API returns 404 rather than reporting the missing parent as an empty collection

### Requirement: Global collection overview
`GET /sites/stats` SHALL return `total_sites`, `total_bins`, `total_capacity_m3` and `bins_by_waste_type` across all stored sites and bins. Above the site list, the UI SHALL display `Surinkimo vietos`, `Konteineriai` with a donut of bin counts by waste type, and `Bendra talpa`. These metrics SHALL be independent of address filters and site pagination.

#### Scenario: Filter the site table without filtering metrics
- **WHEN** an address filter reduces the list to one site
- **THEN** the overview continues to display totals and waste-type counts for the entire stored registry
- **AND** each waste-type category has an identifiable label and count alongside its donut segment

#### Scenario: View statistics with no bins
- **WHEN** there are no bins
- **THEN** total bins displays 0 and the waste-type chart has an explicit empty state
- **AND** the capacity metric displays `N/A`

#### Scenario: Display container counts alongside their donut
- **WHEN** collection overview data is available
- **THEN** container totals/category counts and the donut share one horizontal row
- **AND** glass is green, paper/plastic blue and mixed municipal waste brown

### Requirement: Capacity aggregates preserve unknown values
Global and site capacity SHALL sum stored `capacity_m3` values, ignoring NULLs without converting source units. Known sums SHALL display with `m³`. When no non-NULL capacity exists, the result SHALL remain unknown and display `N/A`. The cubic-metre unit SHALL retain the existing documented, unverified source-unit assumption.

#### Scenario: Sum known capacities alongside NULLs
- **WHEN** a site's bins have capacities 1.1, NULL and 2.5
- **THEN** its total capacity displays 3.6 cubic metres using Lithuanian number formatting

#### Scenario: Distinguish zero capacity from unknown capacity
- **WHEN** one site has only NULL capacities and another has a known sum of zero
- **THEN** the first displays `N/A` and the second displays a numeric zero with `m³`

### Requirement: Informational site location
Site details SHALL show a marker at the stored Site longitude and latitude, with visible street names and surrounding streets. The map SHALL allow panning and zooming by drag, wheel, touch, keyboard and labeled zoom-in/zoom-out controls. Its style SHALL use configurable `VITE_MAP_STYLE_URL`, initially `https://tiles.openfreemap.org/styles/liberty`. Documentation SHALL distinguish imported derived coordinates from manual selected coordinates; viewing SHALL NOT edit either location.

#### Scenario: View the site map
- **WHEN** a site with valid coordinates is opened
- **THEN** the map centers its marker on the stored Site coordinate without swapping latitude and longitude
- **AND** drag can change the map center and wheel, touch, keyboard and the zoom buttons can change the view

#### Scenario: Configure another map style
- **WHEN** the frontend is started or built with a different valid `VITE_MAP_STYLE_URL`
- **THEN** it loads that configured style without requiring map-component changes

#### Scenario: Handle unavailable map resources
- **WHEN** map configuration, coordinates or external map resources are unavailable
- **THEN** the map area shows a clear Lithuanian unavailable/error state, using `N/A` for missing coordinate values
- **AND** site statistics and bins remain usable

#### Scenario: Keep detail locations informational
- **WHEN** an administrator pans, zooms or clicks an existing Site's detail map
- **THEN** the displayed Site marker and stored Site coordinates remain unchanged
- **AND** location selection is available only in the new-Site modal

### Requirement: First-bin site location fields
`GET /sites/{id}` SHALL return site identity, address, coordinates and the location fields `sub_district`, `street`, `house_number` and `postal_code` from the child with the lowest internal `Bin.id`. All four fields SHALL come from that same child. NULLs SHALL NOT be replaced by values from another child. Postal codes and house numbers SHALL retain their text formatting.

#### Scenario: Select the lowest internal child ID
- **WHEN** child IDs are 14 and 27 and bin 14 has NULL street while bin 27 has a known street
- **THEN** all four location fields come from bin 14 and street displays `N/A`

#### Scenario: Preserve geographical text
- **WHEN** the first child's postal code is `08303` and house number is `53A`
- **THEN** details display exactly those values without numeric coercion

### Requirement: Site aggregates cover all child bins
Site details SHALL return and display the count of all child bins, their capacity sum, and distinct non-NULL `object_group` and `waste_carrier` values. Groups SHALL appear comma-separated under `Naudotojai`; carriers SHALL appear comma-separated, with a single value displayed alone. These aggregates SHALL be independent of the current child-bin page. Details SHALL NOT include nested bin history.

#### Scenario: Aggregate bins across multiple pages
- **WHEN** a site has 12 bins with repeated groups and carriers
- **THEN** details count all 12 bins, sum their known capacities and list each non-NULL group and carrier once
- **AND** selecting a different bin page does not change those aggregates

#### Scenario: View a site without child bins
- **WHEN** an existing site has no bins
- **THEN** details remain available with bin count 0 and an explicit empty bin-list state
- **AND** first-bin location fields, capacity, groups and carriers display `N/A`

### Requirement: Paginated child-bin summaries
`GET /sites/{id}/bins` SHALL return a backend-paginated page of that site's bins, with default page 1 and size 10, ordered by internal bin ID ascending. Each item SHALL provide `id`, `inventory_number`, `waste_type` and `capacity_m3`, with standard pagination metadata. Rows SHALL show the latter three fields; activating a row SHALL open the selected bin's dialog.

#### Scenario: Align waste types across bin rows
- **WHEN** bin rows display different capacity lengths in the desktop column layout
- **THEN** every waste-type label starts at the same horizontal position
- **AND** capacity values start at the same horizontal position within their column

#### Scenario: Inspect a bin from a later page
- **WHEN** a user moves to the second bin page and activates a row
- **THEN** the dialog opens for that row's internal bin ID
- **AND** its compact header shows the selected inventory number, waste type and capacity

### Requirement: Service percentages use all stored attempts
`GET /bins/{id}/history` SHALL return `successful_service_percentage` and `unsuccessful_service_percentage` calculated from true and false `was_serviced` counts over all currently stored history for that bin. With history, the dialog SHALL show only the successful-service percentage bar labeled `Sėkmingi aptarnavimai`. The chart SHALL NOT use page-only counts or fill levels.

#### Scenario: Display percentages independently of the history page
- **WHEN** a bin has 82 successful and 18 unsuccessful stored attempts
- **THEN** every history page reports successful percentage 82 and unsuccessful percentage 18
- **AND** the chart displays 82% successful service, without rendering the unsuccessful percentage

#### Scenario: Handle a bin without history
- **WHEN** an existing bin has no history
- **THEN** the API returns total 0, empty items and NULL percentages
- **AND** the dialog displays an empty-history state instead of a `0%` chart

### Requirement: Newest-first paginated bin history
The history endpoint SHALL accept page and page size, both defaulting to 1 and 20 respectively, with maximum size 20. It SHALL return `id`, `date`, `was_serviced`, `non_serviced_reason` and `fill_level` per entry and standard pagination metadata. History SHALL be ordered by date descending and ID descending for ties. The dialog SHALL show entries in a scrollable list, with pagination only for more than one page.

#### Scenario: Order simultaneous successful and unsuccessful attempts
- **WHEN** two stored attempts have the same date and IDs 41 and 42
- **THEN** history shows attempt 42 before attempt 41, behind any later-dated attempts

#### Scenario: Preserve stored wall-clock history time
- **WHEN** an attempt stores the naive date `2026-09-01 08:00:00`
- **THEN** the API returns that date without adding a UTC offset
- **AND** the UI displays the same wall-clock date and time independently of the browser timezone

#### Scenario: Read history in a wide dialog
- **WHEN** a bin with history is opened
- **THEN** the dialog is approximately 1024px wide on desktop, with viewport margins
- **AND** date, status, reason and fill occupy one row per entry
- **AND** history scrolls horizontally on narrow screens and vertically for long pages

### Requirement: Explicit NULL and numeric fill presentation
Every displayed database NULL SHALL appear as `N/A` in lists, metrics, site details, dialog headers and history. Editable form fields SHALL use normal empty inputs instead. Values 0 and false SHALL remain meaningful values. History fill level SHALL display its stored integer 0–3 directly, without category labels, inferred percentages or predictions. API nulls SHALL remain nulls rather than becoming display strings.

#### Scenario: Render nullable bin and history values
- **WHEN** inventory number, capacity, failure reason or fill level is NULL
- **THEN** its displayed field shows `N/A`, never raw null, undefined or an empty NULL placeholder

#### Scenario: Display each numeric fill observation
- **WHEN** attempts have fill levels 0, 1, 2, 3 and NULL
- **THEN** the corresponding displayed values are 0, 1, 2, 3 and `N/A`
- **AND** an unsuccessful boolean status displays its Lithuanian unsuccessful status rather than `N/A`

#### Scenario: Enter an optional missing postal code
- **WHEN** an administrator leaves the new-Site postal-code field empty
- **THEN** the input remains empty, creation stores NULL, and subsequent Site detail display shows `N/A`

### Requirement: Lithuanian responsive and recoverable browsing
Application-controlled text, statuses and known waste-type display labels SHALL be Lithuanian, with `N/A` as the requested missing-value token. Screens and dialogs SHALL follow Trucks styling and remain usable on mobile. Each data area SHALL handle loading and API failure with retry; stale responses SHALL NOT replace a newer selection. Dialogs SHALL support keyboard operation, closing and focus restoration.

#### Scenario: Recover from a history request failure
- **WHEN** fetching a selected bin's history fails
- **THEN** its summary remains identifiable and the dialog shows a Lithuanian error with a retry action
- **AND** retrying performs only another read

#### Scenario: Switch bin selections during a request
- **WHEN** the user closes one bin's dialog and opens another before the first history request completes
- **THEN** the late response does not replace the new bin's history or percentages
- **AND** the new dialog begins at history page 1

#### Scenario: Use browsing on a narrow screen
- **WHEN** the viewport is 320 pixels wide
- **THEN** navigation, rows, map, dialog content and pagination remain readable and operable
- **AND** the scrollable history does not push closing and navigation controls outside reach

#### Scenario: Recover from a missing site
- **WHEN** the selected site endpoint returns 404
- **THEN** the UI shows a Lithuanian site-not-found state and navigation back to the site list

### Requirement: Pagination only for multiple pages
All lists using the shared pagination control, including sites, bins, history and
Trucks, SHALL display pagination only when a known total exceeds page size.

#### Scenario: Hide unnecessary pagination
- **WHEN** a list is empty, contains only one page, or its total is not yet known
- **THEN** its pagination controls are hidden
- **AND** pagination appears when a successful response reports multiple pages

### Requirement: Compact Site list addresses
Site list rows SHALL display only the street name and house number from the registered display address, omitting appended sub-district and postal code. Existing unknown-address fallbacks SHALL remain readable. Full stored addresses, search matching and detail/API address values SHALL remain intact.

#### Scenario: Browse a manually created Site
- **WHEN** a Site has address `Didlaukio g. 53A, Verkių sen., 08303`
- **THEN** its list row shows `Didlaukio g. 53A`
- **AND** its details and deletion confirmation retain the full address
