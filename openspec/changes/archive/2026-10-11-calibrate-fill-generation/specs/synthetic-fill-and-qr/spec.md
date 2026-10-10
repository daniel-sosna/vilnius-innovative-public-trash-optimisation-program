## Purpose

Generate reproducible daily synthetic fullness and lagged QR features with explicitly assumed assessment frequencies and bounded fullness.

## ADDED Requirements

### Requirement: Calibrate the synthetic assessment scenario
Worker assessments SHALL approximately follow 10/20/40/20/10 percent shares for classes 0–4 after unchanged adjacent-class noise. Calibration SHALL be frozen from the first synthetic year and reused on later dates and sensitivities. Reports SHALL show achieved shares by period and acknowledge that the assumed shape is not empirical evidence or a continuous normal distribution.

#### Scenario: Later dates are generated
- **WHEN** dates after the calibration period are generated
- **THEN** the fixed calibration is used without rebalancing those dates or conditioning on a future collection

### Requirement: Bound fullness and preserve source-demand audit
Known fullness SHALL be finite and within 0–120%. Its response to accumulated source demand SHALL be nondecreasing and preserve zero inflow and 0–3% post-service residue. Source-demand volumes SHALL remain separately auditable without being described as physical fill percentages. The old linear volume-to-fullness identity and no-calibration prohibition are superseded.

#### Scenario: Extreme assigned demand
- **WHEN** a small bin receives extreme allocated demand
- **THEN** fullness stays at or below 120% and the original assigned-demand volume remains available in diagnostics

### Requirement: Preserve unrelated generation rules
All original rows and 17 field values, exclusion masks, class thresholds, success/anchor timing, base rates, exposure allocation, calendar/type/district factors, stochastic inputs and 10% worker error SHALL remain unchanged. QR SHALL use the calibrated latent class with its existing intensity, lag and reset equations.

#### Scenario: A zero-exposure residential bin
- **WHEN** a valid residential bin has zero exposure
- **THEN** no demand or QR reports are fabricated to meet the target histogram

### Requirement: Replace and validate generated artifacts
Delivery SHALL include current English rules MD/PDF and change log, enriched CSV, all six diagnostic charts, full-field/domain/bound/timing checks, repeat-run evidence and a realism report. Superseded local generated results SHALL be removed after validated replacement; source exports and the base daily table SHALL remain reproducible inputs.

#### Scenario: Replacement passes verification
- **WHEN** the new full dataset and diagnostics pass their checks
- **THEN** only current generated rule/result versions remain and every substantive rule change is reported
