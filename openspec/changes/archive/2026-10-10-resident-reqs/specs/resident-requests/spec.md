# Spec Delta

## Purpose

Allow residents to identify a physical bin through a public mobile page and submit a request for emptying it, with clear feedback backed by persistent request records.

## ADDED Requirements

### Requirement: Standalone public resident route
The system SHALL serve `/resident-request/{bin_id}` using the existing internal `Bin.id`. The page SHALL be accessible directly without authentication, account selection, admin navigation, or admin layout. Opening or refreshing the URL SHALL load that bin independently of earlier navigation.

#### Scenario: Open a bin URL directly
- **WHEN** a resident opens `/resident-request/12345` for existing internal bin ID 12345
- **THEN** the public resident page loads that bin without the admin navbar or layout
- **AND** an external QR code can point to this URL without the application generating or scanning QR codes

### Requirement: Minimal public bin lookup
`GET /bins/{bin_id}` SHALL resolve the internal primary key and return exactly `id`, `address`, `inventory_number`, `waste_type`, `latitude`, `longitude`, and nullable `latest_service`. Address SHALL come from the bin’s linked collection site; coordinates SHALL locate the physical bin. API nulls SHALL remain nulls. A missing positive ID, including one outside the stored BIGINT range, SHALL return 404. Nonpositive or noninteger IDs SHALL return 422 without modifying records.

#### Scenario: Resolve internal rather than source identity
- **WHEN** a stored bin has internal ID 634 and external ID 135353 and `/bins/634` is requested
- **THEN** the response is 200 with that bin's internal ID, linked site address, inventory number, stored waste type, and physical coordinates
- **AND** it omits external identity, site identity/average coordinates, capacity, and full service history

#### Scenario: Preserve missing inventory information
- **WHEN** the bin's inventory number is NULL
- **THEN** the response contains `inventory_number: null`

#### Scenario: Reject invalid or missing bin references
- **WHEN** the caller requests an absent positive ID or an integer larger than the stored BIGINT range
- **THEN** the response is 404 rather than a database error
- **AND** requesting zero, a negative integer, or noninteger text returns 422

### Requirement: Lithuanian bin identification
The ready page SHALL display `Siųsti šiukšlių išvežimo prašymą`, the bin’s linked site address first under `Adresas`, followed by inventory number under `Konteinerio numeris` and waste type under `Atliekų tipas`. Application-controlled text and known waste-type labels SHALL be Lithuanian. Every displayed nullable value SHALL use `N/A`, preserving meaningful non-null values.

#### Scenario: Identify the selected bin
- **WHEN** a bin with inventory number `00123` and waste type `Glass waste` is loaded
- **THEN** the inventory number displays as `00123` and the waste label is `Stiklo atliekos`
- **AND** the page uses the specified title and field labels

#### Scenario: Use existing known waste labels
- **WHEN** bins have waste types `Mixed municipal waste` and `Paper/plastic waste`
- **THEN** their displayed labels are `Mišrios komunalinės atliekos` and `Popieriaus ir plastiko atliekos`, respectively

#### Scenario: Display a nullable field
- **WHEN** the loaded inventory number is NULL
- **THEN** its displayed value is `N/A`

### Requirement: Fixed bin location map
The ready page SHALL show a map with a marker at the bin’s own coordinates immediately beneath the title and above the address. The map SHALL prevent dragging, touch movement, and wheel, double-click, touch, or keyboard zoom, with no zoom controls. Map loading or failure SHALL NOT prevent reading bin fields or submitting a request.

#### Scenario: Identify the physical location without changing the map
- **WHEN** the resident loads a bin and attempts to drag or zoom its map
- **THEN** the marker shows that bin’s coordinates and the map view remains fixed
- **AND** the map appears before the address, inventory number, and waste type in that order

#### Scenario: Map service is unavailable
- **WHEN** the map cannot load
- **THEN** the resident can still read the address and existing bin fields and submit a request

### Requirement: Latest bin service information
When history exists, the page SHALL centre a pale translucent light-blue Info card with a darker blue icon/border and black text between the fields and button, labelled `Paskutinis aptarnavimas atliktas`. It SHALL display only the latest entry’s calendar date without timezone conversion, ordering by date then ID descending. `latest_service` SHALL contain only `date` and `was_serviced`, or null when absent. No history SHALL mean no card.

#### Scenario: Display the latest history record
- **WHEN** a bin has several history entries
- **THEN** the card displays the newest entry’s stored calendar date under `Paskutinis aptarnavimas atliktas`, without a time
- **AND** an older entry inserted later or another bin’s history does not determine the message

#### Scenario: Latest visit was unsuccessful
- **WHEN** the newest history entry has `was_serviced: false`
- **THEN** the card displays that entry’s date with the requested fixed label
- **AND** it does not fall back to an older successful entry

#### Scenario: No history is available
- **WHEN** no history entry exists for the selected bin
- **THEN** `latest_service` is null and the page displays no service information card or empty placeholder

### Requirement: Distinct loading and not-found states
The page SHALL show loading feedback without an active submit action until bin lookup completes. An absent bin or invalid route ID SHALL display a dedicated, simple mobile state containing `Konteineris nerastas`, with no request form or active `Siųsti` button.

#### Scenario: Wait for bin identification
- **WHEN** the initial bin lookup is pending
- **THEN** the resident receives loading feedback and cannot submit a request

#### Scenario: Open a nonexistent or malformed reference
- **WHEN** lookup returns 404 or the route ID is invalid
- **THEN** the page displays `Konteineris nerastas` without the request form

### Requirement: Recoverable initial loading failure
An initial bin-loading failure other than a missing or invalid ID SHALL display `Kažkas nepavyko. Bandykite dar kartą.` and a `Bandyti dar kartą` action. Retrying SHALL repeat only the bin read. A late response for a previously selected bin SHALL NOT replace the current bin or its state.

#### Scenario: Retry a failed lookup
- **WHEN** loading the bin fails due to a network or server error
- **THEN** the page shows the specified error and retry action without an active submission form
- **AND** a successful retry reveals the correct bin and submit action without creating a request

#### Scenario: Change the bin during loading
- **WHEN** the route changes to another bin while a prior lookup is pending
- **THEN** a late result from the prior lookup cannot replace the new bin's screen

### Requirement: Persist a resident request through the public API
`POST /bins/{bin_id}/resident-requests` SHALL require no request body, resolve the internal bin ID, and create one resident request with a server-generated timestamp. It SHALL return `201 {"success": true}` only after commit. Missing positive IDs SHALL return 404; nonpositive or noninteger IDs SHALL return 422. Failed persistence SHALL return an error without a partial record.

#### Scenario: Commit before confirming success
- **WHEN** the resident submits a POST for an existing bin
- **THEN** one new request is committed with that bin's internal ID and the server's current Vilnius local timestamp
- **AND** the response is 201 with only `success: true`
- **AND** the frontend supplies no timestamp

#### Scenario: Submit after the bin was removed
- **WHEN** the displayed bin has been removed before the POST resolves it
- **THEN** the API returns 404 and creates no detached resident request

#### Scenario: Roll back a failed insert or commit
- **WHEN** persistence fails before the request transaction commits
- **THEN** the API returns a generic server error, creates no committed request, and exposes no database details

#### Scenario: Allow independent repeated reports
- **WHEN** two independent valid POST requests target the same bin
- **THEN** two records with independently generated identities can be stored
- **AND** requests are not deduplicated by bin or timestamp

### Requirement: Submission interaction and recovery
The ready page SHALL have a prominent bottom-positioned `Siųsti` button. One activation SHALL send one submission request; pending submission SHALL prevent repeated activation. A failed submission SHALL show the toast `Kažkas nepavyko. Bandykite dar kartą.`, retain the bin information, omit success feedback, and re-enable `Siųsti` for retry. The page SHALL NOT automatically retry POST requests.

#### Scenario: Avoid repeated clicks during submission
- **WHEN** the resident presses `Siųsti` and attempts to press it again while submission is pending
- **THEN** only one POST is sent for that pending interaction

#### Scenario: Retry after a submission error
- **WHEN** submission fails due to a network error or any non-success API response
- **THEN** the specified error toast appears, bin details remain usable, and `Siųsti` becomes available again
- **AND** the page does not show the confirmation state or automatically resubmit

### Requirement: Successful request confirmation
After successful submission, the page SHALL replace all previous content with a centred large green circle containing a white checkmark, `Jau vykstame pas Jus` underneath, and the supplied responsive GIF below the text. No active `Siųsti` button SHALL remain in that page session. GIF failure SHALL NOT remove or invalidate the textual confirmation. Reloading the page SHALL permit a new submission after loading the bin.

#### Scenario: Show the supplied confirmation
- **WHEN** the API confirms a committed resident request
- **THEN** the page displays the large solid green circle, white checkmark, and exact confirmation text, with no previous title, map, fields, or submit button
- **AND** it displays the GIF from `https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExbzBjbWJnMWNtZXdiYnBpbGZiNTV5NWFydGcyenUzc3N0bmkxMGplMyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/xsFjLwT7NPfH2/giphy.gif` within the page width

#### Scenario: Preserve success when media is unavailable
- **WHEN** the GIF cannot load after a successful submission
- **THEN** the green circle, white checkmark, and confirmation text remain visible and no submit button returns

#### Scenario: Reload after success
- **WHEN** the resident reloads the successful page for a bin that still exists
- **THEN** the bin loads again with a new available submit action
- **AND** loading alone creates no additional request

### Requirement: Mobile-first simplicity and accessibility
The page SHALL be readable and usable at 320px width and adapt to larger screens without horizontal overflow. The main submit button SHALL be full-width within the content column, at least 48px high, and reachable near the bottom with phone safe-area spacing. The page SHALL use a simple single-column presentation, readable text, visible keyboard focus, and accessible state announcements.

#### Scenario: Submit with one hand on a small phone
- **WHEN** the resident opens the page at 320px width
- **THEN** the title, bin values, and submit action fit the content width, long values wrap, and the bottom action remains visible and usable
- **AND** decorative cards, gradients, navigation, and extra animation do not obscure the action

#### Scenario: Operate by keyboard or assistive technology
- **WHEN** the resident navigates with the keyboard or uses a screen reader
- **THEN** the submit and retry actions are operable, focus is visible, and pending, error, and success states are understandable without relying on colour or the GIF

### Requirement: Resident reports remain distinct from operational observations
Saving a resident request SHALL NOT alter bin metadata, service history, fill observations, prediction outputs, collection schedules, or routes. The stored request SHALL represent a resident report rather than verified fill or a service event. This feature SHALL NOT derive or expose requests-since-service counts.

#### Scenario: Store only the resident signal
- **WHEN** a resident request is committed
- **THEN** the bin and its service history retain their values, and no fill level, prediction, route, notification, or derived count is generated
