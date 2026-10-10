# Proposal

## Why

The existing scenario produces mostly class-0 worker assessments and capacity-equivalent backlogs above 16,000%, unsuitable as plausible fullness. The user approved a bell-shaped assessment scenario and a 120% fullness ceiling while retaining other rules.

## What Changes

- Calibrate a monotone bounded response from accumulated source demand to fullness, targeting approximate worker shares 10/20/40/20/10 after the existing 10% adjacent error. Preserve genuine zero exposure rather than forcing exact shares.
- Bound fullness to 0–120%; retain uncapped assigned-demand volume separately for conservation diagnostics. This explicitly supersedes the old linear demand-to-fullness identity and prohibition on calibration.
- Freeze calibration from the first synthetic year; later dates and sensitivity scenarios reuse its parameters. Preserve all original CSV fields, service timing, thresholds, numerical inflow factors, exclusion masks and QR equations.
- Replace English rules, the enriched CSV, six charts and verification/realism reports; remove superseded generated artifacts only after replacements pass.

## Capabilities

### New Capabilities

- `synthetic-fill-and-qr`: Extend the same capability in the completed but unarchived `generate-fill-and-qr-alerts` change. It has no durable main spec yet; these requirements supersede only the named fullness/calibration clauses of that earlier delta.

### Modified Capabilities

None in the main spec inventory. Collection calendar and population allocation contracts remain unchanged.

## Impact

Offline scripts, existing requested tests, generation documentation, local English rules/PDF and ignored data/diagnostics. No API/database changes, predictor training, new service or dependencies. Full coverage inference remains a separate task. Scenario shape and 120% are user-approved assumptions, not measured Vilnius statistics; source-demand conservation does not establish physical conservation of the transformed fullness.
