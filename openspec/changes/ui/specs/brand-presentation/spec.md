# Spec Delta

## Purpose

Give existing VipTop screens a consistent, accessible municipal visual identity while preserving operational workflows and live map presentation.

## ADDED Requirements

### Requirement: Consistent light visual identity
All application screens SHALL use the supplied VipTop Design Kit's light theme: cream background, charcoal text, white surfaces, restrained borders, moderate corners and red primary accents. Typography SHALL use Arial/Helvetica/sans-serif without remote fonts. There SHALL be no dark theme or theme switcher.

#### Scenario: Visit operational and public screens
- **WHEN** a user opens role selection, admin fleet/sites/bin detail, map analytics, demo/routes, driver, resident or not-found screens
- **THEN** each uses the same palette, typography and spacing conventions without a separate visual system
- **AND** body text is approximately 16/24px, secondary text 14/21px, titles remain appropriate to operational screens, spacing follows 4/8/12/16/24/32/48/64px and standard corners are approximately 10px

#### Scenario: Device requests dark appearance
- **WHEN** the operating system prefers dark mode
- **THEN** VipTop retains its light appearance

### Requirement: Supplied local branding
VipTop SHALL use the supplied charcoal `Vip` and red skewed `Top` wordmark. City branding SHALL use the supplied transparent red Vilnius artwork with original proportions and secondary prominence. Supplied wolves SHALL be used selectively in welcome, branded empty or confirmed-success states without obscuring working maps or data.

#### Scenario: Recognize the application
- **WHEN** a user visits role selection or admin navigation
- **THEN** the supplied wordmark is visible and existing logo links retain their destinations and accessible names
- **AND** the city asset is neither stretched nor recolored nor placed on an unnecessary opaque block

#### Scenario: View data-heavy screens
- **WHEN** a user operates maps, tables or driver navigation
- **THEN** mascot decoration does not obscure controls, attribution or information
- **AND** branding uses local assets without external GIF or font services

### Requirement: Shared controls and operational states
Primary controls SHALL use `#ce202f`, white text and `#aa1724` hover; secondary controls SHALL remain neutral. Destructive controls SHALL use `#b91c1c`, and success SHALL use `#2f6b45` with textual context. Forms SHALL use white surfaces, visible borders and labels; tables SHALL retain restrained rows and borders rather than individual floating cards.

#### Scenario: Operate a form or table
- **WHEN** a user edits trucks, sites, bins or collections
- **THEN** validation, loading, disabled, error and empty feedback remains understandable
- **AND** existing CRUD actions, filters, pagination and sorting where present retain their behavior

### Requirement: Data signal colors remain distinct
Waste and risk colors SHALL retain existing meanings and map colors. Non-map fill swatches SHALL use levels 0–4: `#8ea991`, `#adc1a0`, `#d9bf76`, `#df9b36`, `#ce202f`, with readable text. Numeric levels, labels, provenance and recorded values SHALL remain unchanged; brand red SHALL NOT replace all data categories.

#### Scenario: Read map legends
- **WHEN** waste or risk legends are shown
- **THEN** waste swatches remain paper/plastic `#2563eb`, glass `#15803d`, mixed `#92400e`, other `#6b7280`, cluster `#64748b`
- **AND** risk swatches remain priority `#dc2626`, potential `#d97706`, frequent level 4 `#7c3aed`, ordinary `#6b9278`, insufficient evidence `#9ca3af`, unavailable `#d1d5db`

#### Scenario: Record a driver observation
- **WHEN** a driver chooses a fill level
- **THEN** the supplied swatch has a readable number, existing label and distinguishable selection state
- **AND** the chosen numeric value and advance/back/save workflow remain unchanged

### Requirement: Live map rendering is preserved
Visual redesign SHALL preserve live map styles, basemaps, tiles, sources, attribution, domain colors, markers, clusters, polygons, routes, camera and interaction behavior. Static design previews SHALL NOT replace live maps. Functional route drawing, truck movement and navigation animation SHALL remain intact.

#### Scenario: Compare maps across the redesign
- **WHEN** the same data and camera are displayed on analytics, demo, driver or location maps
- **THEN** map rendering and domain features retain their appearance and meaning
- **AND** existing zoom, pan, selection, navigation and read-only-map constraints still apply

### Requirement: Map surrounding UI and popup theme
Map headers, sidebars, legends, floating buttons, analysis panels, loading UI and popup typography, borders and surfaces SHALL adopt the VipTop theme. Popup content and interactions SHALL remain unchanged. Overlays SHALL preserve reachable attribution, map controls and selection actions; floating controls SHALL remain opaque.

#### Scenario: Open a popup and sidebar
- **WHEN** a user opens a map popup or switches between layers and AI
- **THEN** the new surfaces and typography are applied without changing displayed values, analytical text or actions
- **AND** layer selections, filters, confirmed area, analysis state and camera are retained

### Requirement: Responsive accessible operational layouts
Screens SHALL remain usable at 320px, approximately 390px, tablet and 1440px widths without page-wide horizontal overflow. Mobile control targets SHALL be at least 44px; resident submit SHALL remain at least 48px. Dialogs SHALL fit the viewport, long Lithuanian labels SHALL wrap and wide tables SHALL remain accessible through local scrolling.

#### Scenario: Operate on a phone
- **WHEN** a user opens mobile navigation, a form, table, dialog or map panel
- **THEN** controls fit or scroll within their own bounded region, remain touch-friendly and leave maps properly sized
- **AND** driver screens remain map-dominant with large controls and minimal text

#### Scenario: Navigate by keyboard
- **WHEN** a user moves through controls or dismisses a menu/dialog/sidebar
- **THEN** semantic controls, labels, accessible names, visible focus, existing Escape handling and focus restoration remain available
- **AND** pending, errors and success retain appropriate announcements and do not rely solely on color

### Requirement: Navigation and workflows remain intact
The theme SHALL preserve routes, mobile menu behavior, shared project date and calendar locking, API contracts, data semantics, resident submission, driver workflow, demo pipeline and AI behavior. Reference-screen demo values and actions SHALL NOT become invented application data or new workflows.

#### Scenario: Navigate between admin screens
- **WHEN** the user changes project date and visits fleet, sites, analytics and routes
- **THEN** existing links and shared date behavior remain intact
- **AND** no restyling resets page state or bypasses existing disabled states

### Requirement: Restrained general motion
Outside the dedicated launch sequence, decorative motion SHALL be restrained and respect reduced motion. Hover/reveal/confirmation timing SHALL follow approximately 140/240/up to 360ms. Existing functional map and progress animations SHALL NOT be removed or redesigned by the visual change.

#### Scenario: Prefer reduced motion
- **WHEN** reduced motion is enabled
- **THEN** decorative reveals or mascot animation are suppressed without hiding status text
- **AND** existing functional animation logic is preserved with its existing accessibility behavior
