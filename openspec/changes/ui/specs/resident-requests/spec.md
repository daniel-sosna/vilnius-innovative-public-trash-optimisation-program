# Spec Delta

## MODIFIED Requirements

### Requirement: Latest bin service information
When history exists, the page SHALL centre a themed information panel with an Info icon, readable charcoal text and restrained border between the fields and button, labelled `Paskutinis aptarnavimas atliktas`. It SHALL display only the latest entry’s calendar date without timezone conversion, ordering by date then ID descending. `latest_service` SHALL contain only `date` and `was_serviced`, or null when absent. No history SHALL mean no panel.

#### Scenario: Display the latest history record
- **WHEN** a bin has several history entries
- **THEN** the panel displays the newest entry’s stored calendar date under `Paskutinis aptarnavimas atliktas`, without a time
- **AND** an older entry inserted later or another bin’s history does not determine the message

#### Scenario: Latest visit was unsuccessful
- **WHEN** the newest history entry has `was_serviced: false`
- **THEN** the panel displays that entry’s date with the requested fixed label
- **AND** it does not fall back to an older successful entry

#### Scenario: No history is available
- **WHEN** no history entry exists for the selected bin
- **THEN** `latest_service` is null and the page displays no service information panel or empty placeholder

### Requirement: Successful request confirmation
After successful submission, the page SHALL replace all previous content with a centred success presentation containing a green status indicator, the exact text `Pranešimas gautas`, and supplied local VipTop branding/mascot. No active `Siųsti` button SHALL remain in that page session. Artwork failure SHALL NOT remove or invalidate textual confirmation. Reloading the page SHALL permit a new submission after loading the bin. The message SHALL confirm receipt without promising truck dispatch or arrival.

#### Scenario: Show the supplied confirmation
- **WHEN** the API confirms a committed resident request
- **THEN** the page displays a green success indicator and `Pranešimas gautas`, with no previous title, map, fields, or submit button
- **AND** the supplied local branding/mascot fits within the page width without an external GIF request
- **AND** success is announced through accessible status text rather than decoration alone

#### Scenario: Preserve success when media is unavailable
- **WHEN** local artwork cannot load after a successful submission
- **THEN** the success indicator and confirmation text remain visible and no submit button returns

#### Scenario: Reload after success
- **WHEN** the resident reloads the successful page for a bin that still exists
- **THEN** the bin loads again with a new available submit action
- **AND** loading alone creates no additional request

### Requirement: Centered Vilnius logo before resident request success
The public `/resident-request/{bin_id}` page SHALL show the supplied full Vilnius emblem and wordmark horizontally centered at the top of its content, above the title, in every pre-success state, with the VipTop wordmark included in the branded header. The logo SHALL add no navigation or authentication requirement. After successful submission, the pre-success header SHALL disappear along with previous content as the branded confirmation replaces the page.

#### Scenario: Open the resident page directly
- **WHEN** a resident opens or refreshes a valid bin URL
- **THEN** the Vilnius logo appears centered above the title during loading and after the bin loads, with a readable VipTop wordmark
- **AND** the page remains independent of the admin navbar and role selection

#### Scenario: Show lookup failure or missing bin
- **WHEN** the lookup fails, the bin does not exist, or the route ID is invalid
- **THEN** the branded header remains above the corresponding title
- **AND** the existing error, retry, or not-found content remains usable

#### Scenario: Submit and recover
- **WHEN** a resident submits a request and submission is pending or fails
- **THEN** the branded header remains above the title and bin details
- **AND** existing pending protection and failed-submission retry behavior remain available

#### Scenario: Replace the branded form after success
- **WHEN** the API confirms successful submission
- **THEN** the header and prior request content are replaced by the branded success indicator, `Pranešimas gautas` and local mascot
- **AND** no submit button remains in that page session
