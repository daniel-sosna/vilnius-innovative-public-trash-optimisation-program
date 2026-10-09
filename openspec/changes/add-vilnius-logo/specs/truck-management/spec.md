# Spec Delta

## ADDED Requirements

### Requirement: Vilnius logo at the top of role selection
The `/` page SHALL show the supplied full Vilnius emblem and wordmark horizontally centered near the top of the viewport, above the existing VipTop branding, role-selection heading, and role buttons. The existing role-selection actions and VipTop leaf branding SHALL remain available as before.

#### Scenario: Open role selection
- **WHEN** a visitor opens or refreshes `/`
- **THEN** the Vilnius logo appears centered near the page top, above the role-selection content
- **AND** `Administratorius` still opens `/admin/trucks` and `Vairuotojas` remains disabled

### Requirement: Vilnius logo in shared administrator navigation
All admin screens SHALL display the supplied full Vilnius logo at the right of the shared navbar, with the existing VipTop leaf branding on the left. Both branding links SHALL provide a home action to `/`. The city logo SHALL remain visible when mobile navigation is closed or open, without obstructing navigation controls.

#### Scenario: Visit each administrator route
- **WHEN** an administrator opens `/admin/trucks`, `/admin/sites`, or `/admin/sites/{id}`
- **THEN** the same Vilnius logo appears at the navbar's right edge, with VipTop on the left
- **AND** activating either branding home action returns to `/`

#### Scenario: Use narrow-screen navigation
- **WHEN** an administrator opens the mobile menu at 320px width
- **THEN** the logo remains at the right of the top navbar row, and VipTop branding, menu toggle, and expanded navigation fit the viewport
- **AND** selecting a link closes the menu, and Escape closes it and returns focus to the toggle

### Requirement: Responsive and accessible Vilnius identity on entry and admin screens
The Vilnius logo SHALL retain its supplied red artwork, transparency, full emblem and wordmark, and original proportions. It SHALL have an accessible Lithuanian description identifying the city logo, display more compactly in the navbar than on `/`, and fit at 320px width without causing horizontal overflow.

#### Scenario: Recognize the supplied identity
- **WHEN** a visitor views `/` or an admin screen on desktop or at 320px width
- **THEN** the full emblem and wordmark are visible without stretching, clipping, or an added opaque background
- **AND** assistive technology can identify it as the Vilnius logo

#### Scenario: Use the logo after deployment
- **WHEN** a visitor loads a deployed page without access to the developer's local files
- **THEN** the logo loads as an application asset without depending on a Downloads directory or third-party image host
