# Archive reconciliation — 2026-10-11

All five implementation tasks are complete. This change contributes the six
base requirements and the original Purpose of the new
`openspec/specs/synthetic-fill-and-qr/spec.md` main spec.
`calibrate-fill-generation` contributes four additional requirements to the
same capability. Both deltas are retained unchanged in the archive, and the
combined contract preserves source rows, service timing, source-demand
conservation, lagged QR counts, reproducibility and validation while making
the agreed bounded, calibrated fullness scenario explicit.

The final replacement's evidence is retained under
`backend/data/validation/fill_qr/`: 20 recorded passing unit tests, a passing
pipeline fixture, full verification of 23,777,720 rows and two identical full
generation runs. At archive time the current input/output, generator-source,
rules-PDF and six chart hashes were checked against those records.
No data regeneration or model training was performed during archival.
