# synthetic-fill-and-qr Specification

## Purpose

Generate reproducible synthetic fill assessments and lagged QR counts from existing daily bin exports, with explicit uncertainty and validation evidence.

## Requirements

### Requirement: Preserve the input dataset
The offline generator SHALL preserve every input row, its order and all original field values, appending only nullable integer `fill_level` and `qr_alerts`. Invalid categories, capacities, exposures or unresolved districts SHALL produce NULL in both outputs and an audit entry per affected bin.

#### Scenario: Invalid bin remains present
- **WHEN** a bin has no supported object category or a non-positive capacity
- **THEN** all its original rows remain present with both new fields NULL and a documented exclusion reason

### Requirement: Respect service timing and unknown state
Only `collected` and `retry_collected` SHALL empty a bin. The first successful collection SHALL anchor the unknown initial state, with both outputs NULL that day. Later fill assessments SHALL occur before successful emptying only; failed, missed and absent collections SHALL not receive fill labels or reset state.

#### Scenario: First observed success
- **WHEN** a bin first succeeds after several input days
- **THEN** no initial fill or QR count is invented, and the following day starts from a sampled residual fill

### Requirement: Generate conserved daily waste
The generator SHALL retain the supplied rates, calendar factors, type multipliers and stochastic distributions. It SHALL use existing per-bin resident exposure, share a 100-user fallback across non-residential bins at each physical site and stream, and conserve each site/stream daily inflow across its valid bins. Zero residential exposure SHALL remain zero.

#### Scenario: Mixed object categories
- **WHEN** one site contains several supported object categories
- **THEN** each category contributes its documented multiplier without duplicating the site's fallback population

### Requirement: Keep QR features lagged
`qr_alerts` SHALL count synthetic reports since the latest successful collection through yesterday. Reports SHALL follow the supplied Poisson intensity based on the latent pre-collection fill class. Today's reports and service outcome SHALL not affect today's QR feature.

#### Scenario: Successful service resets tomorrow's count
- **WHEN** today's service succeeds
- **THEN** today's QR feature still reflects yesterday's history and tomorrow's feature is zero

### Requirement: Reproduce and audit generation
Identical input, parameters and seed SHALL reproduce outputs independently of processing order. The generator SHALL reject duplicate/conflicting daily rows and inconsistent static fields, and record input/output hashes, assumptions, exclusions, parameters and software versions.

#### Scenario: Repeat a generation
- **WHEN** the same full date range is generated twice with seed 20261009
- **THEN** the resulting output values and file hashes match

### Requirement: Validate without claiming measured accuracy
Validation SHALL include requested automated tests, full row-preservation and domain checks, representative trajectories, distribution charts and paired sensitivity scenarios. Reports SHALL distinguish internal consistency from empirical accuracy and mark annual mass validation unavailable without a justified bulk density.

#### Scenario: No measured fill history
- **WHEN** all available historical fill observations are NULL
- **THEN** validation describes simulation behavior and cannot report measured fill prediction accuracy

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
