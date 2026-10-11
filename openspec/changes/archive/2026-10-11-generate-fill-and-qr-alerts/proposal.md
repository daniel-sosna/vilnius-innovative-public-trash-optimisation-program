# Proposal

## Why

The three-year bin-day CSV has collection and population features but no fill target or QR signal. The supplied v2.1 rules use a different schema and assumptions about site homogeneity that conflict with the actual exports.

## What Changes

- Adapt only incompatible rule passages, retain the original numerical assumptions, and publish English Markdown, PDF and a complete change log in `backend/data/rules/`.
- Add an offline, reproducible generator that preserves every existing field and row and appends nullable `fill_level` (0-4) and `qr_alerts` (reports through yesterday).
- Use existing synthetic collection outcomes, per-bin resident allocations, reviewed district aliases and shared non-residential site exposure. Keep invalid bins with both outputs NULL and an exclusion audit, as explicitly approved by the user.
- Generate the complete 2023-10-10..2026-10-09 enriched dataset, tests, diagnostic charts and paired sensitivity analysis. Distinguish internal consistency from unverified real-world accuracy.

## Capabilities

### New Capabilities

- `synthetic-fill-and-qr`: Offline generation and auditable validation of synthetic worker fill assessments and lagged QR counts from bin-day exports.

### Modified Capabilities

None. Existing calendar, database and HTTP contracts remain unchanged.

## Impact

- New Python analysis scripts and explicitly requested automated tests; NumPy, SciPy, holidays, matplotlib and ReportLab are analysis dependencies only.
- Local output CSVs, diagnostics and source-rule copies remain under the existing git-ignored `backend/data/` directory. Executable source, tests and reproduction documentation are versioned.
- Important assumptions: registry/population snapshots remain constant for three years; October schedules already generated synthetic service outcomes; no measured fill labels, event feed or verified waste bulk density are available.
- No model training, database migration, service deployment, QR application or VASA synchronization is introduced.
