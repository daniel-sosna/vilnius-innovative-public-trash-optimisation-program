# Spec Delta

## ADDED Requirements

### Requirement: Centered Vilnius logo before resident request success
The public `/resident-request/{bin_id}` page SHALL show the supplied full Vilnius emblem and wordmark horizontally centered at the top of its content, above the title, in every pre-success state. The logo SHALL add no navigation or authentication requirement. After successful submission, it SHALL disappear along with the previous content as the existing confirmation replaces the page.

#### Scenario: Open the resident page directly
- **WHEN** a resident opens or refreshes a valid bin URL
- **THEN** the logo appears centered above the title during loading and after the bin loads
- **AND** the page remains independent of the admin navbar and role selection

#### Scenario: Show lookup failure or missing bin
- **WHEN** the lookup fails, the bin does not exist, or the route ID is invalid
- **THEN** the logo remains centered above the corresponding title
- **AND** the existing error, retry, or not-found content remains usable

#### Scenario: Submit and recover
- **WHEN** a resident submits a request and submission is pending or fails
- **THEN** the logo remains above the title and bin details
- **AND** existing pending protection and failed-submission retry behavior remain available

#### Scenario: Replace the branded form after success
- **WHEN** the API confirms successful submission
- **THEN** the logo and prior request content are replaced by the existing green checkmark, confirmation text, and responsive GIF
- **AND** no submit button remains in that page session

### Requirement: Responsive and accessible resident city logo
The resident logo SHALL preserve its supplied red artwork, transparency, full emblem and wordmark, and original proportions, with an accessible Lithuanian description identifying the city logo. At 320px width it SHALL fit without horizontal overflow or obscuring the request and retry actions. It SHALL load as an application asset without requiring a developer-local path or third-party image host.

#### Scenario: Read the form on a phone
- **WHEN** a resident views the page at 320px width
- **THEN** the full logo fits above the title without stretching, clipping, or an added opaque background
- **AND** the map, fields, service information, and bottom-positioned submit action remain readable and reachable

#### Scenario: Identify city branding with assistive technology
- **WHEN** a resident reads the pre-success page using a screen reader
- **THEN** the image has a Lithuanian description identifying the Vilnius logo
- **AND** its presence does not alter the existing page heading or state announcements
