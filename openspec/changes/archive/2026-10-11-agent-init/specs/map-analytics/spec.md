# Spec Delta

## MODIFIED Requirements

### Requirement: Large interactive Vilnius map
The screen SHALL fill the available viewport width and height below the existing admin navigation with a map initially centered on Vilnius. Users SHALL be able to pan and zoom with mouse, touch and keyboard, use labeled zoom controls, and activate displayed features outside area selection. The map SHALL have no surrounding dashboard card, permanent side column, large visible heading or content-width padding. Controls SHALL use a shared overlay sidebar with internal scrolling, usable at 320-pixel widths.

#### Scenario: Explore the city
- **WHEN** the screen opens on desktop
- **THEN** the map occupies all available viewport space below the admin navigation and supports pan, zoom and feature interaction
- **AND** its layer/legend controls are reachable through a floating button and overlay sidebar

#### Scenario: Scroll a long layer list
- **WHEN** registered layers exceed the available sidebar height
- **THEN** the sidebar scrolls internally while both headings and the legend remain reachable and the map retains its available viewport size

#### Scenario: Use a narrow screen
- **WHEN** the screen is viewed at 320 pixels wide
- **THEN** navigation, layer controls, map controls and popup content remain reachable without page-wide horizontal scrolling
- **AND** the sidebar becomes a responsive panel over the map rather than permanently reducing the map to a small content area

#### Scenario: Focus through pointer and keyboard interaction
- **WHEN** an administrator clicks or touches the map canvas
- **THEN** the canvas does not display a focus outline
- **AND** keyboard navigation still provides a visible focus indicator

## ADDED Requirements

### Requirement: Separate floating controls share one sidebar
The map SHALL expose separate floating layers/legend and AI buttons with accessible Lithuanian labels and clear active states. Either button SHALL open or switch the same sidebar container to its corresponding mode. No more than one shared sidebar SHALL be open at a time.

#### Scenario: Switch from layers to AI
- **WHEN** the layers sidebar is open and the AI button is activated
- **THEN** the existing sidebar switches to AI content without opening another panel

#### Scenario: Switch from AI to layers
- **WHEN** the AI sidebar is open and the layers button is activated
- **THEN** the same sidebar displays layer controls followed by the legend

### Requirement: Closing and switching overlays preserves map state
Closing or switching the sidebar SHALL preserve the map instance, center, zoom, bearing, pitch, active layers, filters and cached data. It SHALL not clear confirmed AI selection or analysis state. Explicit map-failure recovery remains permitted to recreate the map.

#### Scenario: Close after exploring
- **WHEN** the administrator pans, zooms, filters bins and then closes either sidebar mode
- **THEN** the full map view retains its camera, datasets, filters and any confirmed analytical area
- **AND** no basemap recreation or layer refetch is caused by closing

### Requirement: Responsive accessible sidebar and floating controls
Desktop SHALL use a fixed-width overlay sidebar; mobile SHALL use a bounded responsive panel with internal scrolling. Close controls, Escape dismissal and focus restoration SHALL be available. Floating buttons, map zoom, attribution and selection actions SHALL remain reachable without overlapping each other or the admin navigation.

#### Scenario: Close with a keyboard
- **WHEN** the administrator presses Escape while using an open sidebar outside selection mode
- **THEN** the sidebar closes and focus returns to its floating trigger

#### Scenario: Operate on a phone
- **WHEN** the sidebar is opened at 320-pixel width
- **THEN** its actions and content fit the viewport with internal scrolling and an accessible close control
- **AND** closing restores the map area without changing its camera

#### Scenario: Admin navigation changes height
- **WHEN** mobile navigation is expanded or viewport dimensions change
- **THEN** the map and panel adapt to the space below the navigation without covering it or causing page-wide horizontal scrolling

### Requirement: Opaque floating controls
The AI and layer controls SHALL have opaque backgrounds in active, inactive and hover states so map details do not show through them.

#### Scenario: Controls above map data
- **WHEN** either floating control appears above map features
- **THEN** its background remains opaque and its icon is readable
