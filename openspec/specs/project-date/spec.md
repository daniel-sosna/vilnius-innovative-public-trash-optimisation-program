# project-date Specification

## Purpose

Provide one shared calendar day for the application's September demonstration, with consistent next-day forecasting context and a lock while planning is active.

## Requirements

### Requirement: September project calendar
The shared administrator navbar SHALL offer a calendar icon and date picker limited to September 1–30, 2026. The selected date SHALL be visible or directly discoverable and represented as a date-only `YYYY-MM-DD` value throughout the application.

#### Scenario: Select a September day
- **WHEN** the administrator selects September 14
- **THEN** the shared date is `2026-09-14` and is identifiable from the navbar
- **AND** dates outside September 2026 cannot be selected

#### Scenario: Calendar on mobile
- **WHEN** the calendar is opened at 320 pixels wide or operated by keyboard
- **THEN** the controls are usable without horizontal page scrolling and preserve navbar branding and navigation access

### Requirement: One persistent application date
All frontend features SHALL consume the same selected project date. Navigation and refresh SHALL preserve a valid selection using local persistence. An absent, invalid or out-of-range stored value SHALL initialize to `2026-09-14`; unavailable persistence SHALL leave selection functional for the current application session.

#### Scenario: Navigate and refresh
- **WHEN** September 20 is selected and the administrator visits Demo, Map Analytics and refreshes
- **THEN** each screen observes `2026-09-20`

#### Scenario: Recover an unusable stored date
- **WHEN** persisted selection is malformed or `2026-10-11`
- **THEN** the selected project date is `2026-09-14`

#### Scenario: Avoid timezone shifts
- **WHEN** the same persisted date is loaded in browsers with different timezones
- **THEN** its calendar day and API string are unchanged

### Requirement: Selected day and forecast day
The selected project date SHALL mean input day T for prediction. Demo SHALL distinguish this date from forecast/service day T+1, and SHALL send T unchanged to prediction. October 1 SHALL be a valid forecast day after a September 30 selection.

#### Scenario: Mid-month forecast
- **WHEN** the selected project date is `2026-09-14`
- **THEN** prediction receives `2026-09-14` and Demo identifies the resulting routes as for `2026-09-15`

#### Scenario: Month boundary
- **WHEN** the selected project date is `2026-09-30`
- **THEN** prediction and route results refer to `2026-10-01` without permitting October input selection

### Requirement: Lock selection during planning
The application SHALL disable global date changes from demo start through prediction, route calculation and drawing. Completion, empty prediction, any stage failure or leaving Demo SHALL release the lock. A reload SHALL not restore a stale lock.

#### Scenario: Keep the date fixed throughout a run
- **WHEN** a run is predicting, calculating routes or drawing them
- **THEN** the navbar date control is disabled and the selected day cannot change

#### Scenario: Release the lock
- **WHEN** the run completes, fails, finds no service bins, or the administrator leaves Demo
- **THEN** the calendar becomes usable and the selected date remains unchanged

#### Scenario: Reload during inference
- **WHEN** the administrator refreshes during an active run
- **THEN** the persisted date is retained but the calendar is unlocked and no unfinished run is restored
