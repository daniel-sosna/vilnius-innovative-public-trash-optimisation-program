# Spec Delta

## Purpose

Present the supplied VipTop launch sequence on each full application load while allowing initialization to proceed and guaranteeing access to the application.

## ADDED Requirements

### Requirement: Supplied per-load launch presentation
Each new application opening, full refresh or direct route load SHALL show the supplied launch sequence once for that application load. Internal navigation SHALL NOT replay it. Historical visits SHALL NOT suppress it through cookies or browser storage. There SHALL be no additional generic full-screen splash or spinner.

#### Scenario: Open entry routes
- **WHEN** the user opens or hard-refreshes `/`, an admin route, a driver route or `/resident-request/123` directly
- **THEN** the launch sequence appears for the new application load

#### Scenario: Navigate internally
- **WHEN** a user navigates through application links after the launch ends
- **THEN** the launch sequence does not replay

### Requirement: Exact source interval and playback
Normal launch playback SHALL render the supplied source interval 13.5–15.0 seconds over 3 seconds of real elapsed playback after local images are ready. It SHALL preserve supplied artwork, movement, red transition, title, branding and wolf wink, without audio. It SHALL neither replay nor wait through the first 13.5 seconds. Only launch transition and closing artwork SHALL be visible; preceding presentation scenes and partially decoded images SHALL remain hidden.

#### Scenario: Assets become ready
- **WHEN** local artwork is ready and playback starts
- **THEN** the first rendered playback frame corresponds to source time 13.5 seconds and completion corresponds to 15.0 seconds after 3 seconds of elapsed playback
- **AND** presentation duration does not depend on frame count; normal completion holds the final composition for approximately 250ms before dismissing the overlay

### Requirement: Concurrent initialization and interaction isolation
The application SHALL initialize immediately beneath a full-viewport cream `#f6f1e8` launch overlay. Underlying content SHALL be unavailable to pointer, keyboard and assistive-technology interaction while the overlay is active. Completion SHALL restore access without remounting the application or implying data loading has finished.

#### Scenario: Initialize data during launch
- **WHEN** the launch overlay is active on a data or map screen
- **THEN** ordinary application, API and map initialization proceeds underneath
- **AND** the user cannot activate underlying controls

#### Scenario: Data remains pending
- **WHEN** the overlay closes before page data finishes loading
- **THEN** the already-mounted page displays its ordinary local loading state without another full-screen splash

### Requirement: Automatic launch dismissal
The overlay SHALL show no skip button. Playback completion or launch failure SHALL dismiss it automatically and restore application interaction and valid keyboard focus.

#### Scenario: Complete playback
- **WHEN** the launch completes or its failure deadline expires
- **THEN** the overlay disappears automatically without user action
- **AND** keyboard focus is not left in removed overlay content

### Requirement: Failure cannot block application access
Launch failure SHALL dismiss the overlay and restore application access. Missing files, image decoding failure, missing completion notification or stalled initialization SHALL never hold access beyond a default maximum of 6000ms from overlay mounting, subject to browser timer scheduling.

#### Scenario: Launch document or images fail
- **WHEN** the launch document fails or artwork cannot decode
- **THEN** the overlay is dismissed on detected failure or by the maximum wait

#### Scenario: Completion is never received
- **WHEN** launch startup or completion stalls
- **THEN** the application becomes accessible by the six-second fail-safe without user action

### Requirement: Reduced-motion composition
With reduced motion requested, the launch SHALL display the supplied static final composition for approximately 450ms after readiness instead of full motion. Branding SHALL remain visible; the failure deadline SHALL still apply.

#### Scenario: Open with reduced motion
- **WHEN** a reduced-motion user opens an entry route
- **THEN** the final composition is shown without the animated transition or wink sequence and the application is revealed after approximately 450ms

### Requirement: Responsive artwork without timeline restart
The launch SHALL cover desktop, tablet and phone viewports in portrait and landscape without stretching artwork. The landscape scene SHALL scale proportionally to cover the full viewport, cropping outer edges when the viewport differs from 16:9; portrait SHALL use the supplied vertically arranged final composition. Rotation SHALL recalculate layout without restarting playback.

#### Scenario: View small portrait phones
- **WHEN** the sequence is viewed on a small phone, Android phone or iPhone in portrait
- **THEN** logos and title remain readable, artwork keeps its proportions and the composition respects safe areas

#### Scenario: Rotate during playback
- **WHEN** the viewport orientation changes during the sequence
- **THEN** composition adapts and playback retains its elapsed time and original completion deadline

### Requirement: Local isolated launch assets
Launch artwork and playback SHALL be self-hosted without remote videos, GIFs, fonts or animation services. The animation SHALL remain isolated from application styles and identifiers. Startup and completion notifications SHALL be accepted only from the expected source, origin and launch instance.

#### Scenario: Launch without external asset services
- **WHEN** the application serves the launch document
- **THEN** the sequence requires no third-party asset requests or autoplay video permission
- **AND** application styles do not change animation artwork or layout

#### Scenario: Ignore unrelated notifications
- **WHEN** an unrelated source, origin or instance sends a start or completion notification
- **THEN** it does not start or dismiss the active launch sequence
