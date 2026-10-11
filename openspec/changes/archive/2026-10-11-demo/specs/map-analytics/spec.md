# Spec Delta

## ADDED Requirements

### Requirement: Shared project date access
Map Analytics SHALL observe the application-wide project date without initializing or persisting its own independent selection. Introducing date access SHALL preserve existing dataset loading, filtering, map camera and agent analytics behavior; date selection alone SHALL not trigger analytics requests.

#### Scenario: Share the Demo selection
- **WHEN** the administrator selects September 14 in Demo and opens Map Analytics
- **THEN** Map Analytics observes `2026-09-14` through the shared date state and the navbar shows the same selection

#### Scenario: Change date in Map Analytics
- **WHEN** the administrator changes the navbar date while viewing Map Analytics
- **THEN** the shared date updates without resetting layer selections, moving the map camera or automatically starting agent analysis
- **AND** Demo observes that same date when subsequently opened
