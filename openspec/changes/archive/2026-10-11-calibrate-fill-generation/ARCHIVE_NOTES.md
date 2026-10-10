# Archive reconciliation — 2026-10-11

All four implementation tasks are complete. The four calibration requirements
are added to the six base requirements from `generate-fill-and-qr-alerts` in
the same `synthetic-fill-and-qr` main spec. The base spec's Purpose is retained;
this delta's Purpose does not replace it.

The current contract explicitly preserves source-demand audit and unchanged
generation rules while using first-year frozen calibration and bounded
fullness. Both original deltas remain available as archive history.

Current artifacts match the recorded input/output, source, PDF and chart
hashes. The retained evidence records 20 passing unit tests, a passing
pipeline fixture, full verification of 23,777,720 rows and two reproducible
generation runs. Archival changes only OpenSpec documentation; the historical
training CSV and delivered predictor are unchanged.
