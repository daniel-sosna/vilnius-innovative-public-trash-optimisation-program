# Synthetic fill and QR generation

Run from the repository root on `ml-training`, with Python 3.12. The scripts are offline and do not need a database. The outputs are synthetic scenarios, not measured labels. Dependencies are isolated from the backend application:

```powershell
python -m pip install -r scripts/requirements-fill-qr.txt
python -X utf8 scripts/adapt_fill_qr_rules.py --source C:/Users/Admin/Downloads/vilnius_two_column_generation_rules_v2.md
python -X utf8 -m unittest discover -s scripts/tests -v
python -X utf8 scripts/tests/check_fill_qr_pipeline.py
python -X utf8 scripts/fill_qr.py
python -X utf8 scripts/validate_fill_qr.py
```

The input defaults to `backend/data/bin_days_20231010_20261009.csv`; the new output is `backend/data/bin_days_20231010_20261009_enriched.csv`. Existing output files require `--overwrite`. Both the original table and all original field values are retained. Only nullable `fill_level` and `qr_alerts` are appended. An empty CSV field is NULL; class 0 and counter 0 have different meanings.

The CLI also accepts `--input`, `--output`, `--start`, `--end`, `--seed`, `--bins`, `--population`, `--schedule`, `--rules` and `--diagnostics`. The input must be grouped by bin, with consecutive ordered dates covering the entire requested range and the existing 17-column schema. Registry/population/schedule exports establish the expected eligible roster. The generator rejects missing/duplicate dates, unknown statuses and changing static attributes, publishing the CSV only after a complete run.

Version 4 retains numerical inflow, allocation, worker-error and QR rules, changing only the fullness response and assumed assessment shape. Approximate worker shares are 10/20/40/20/10 and known fullness is bounded to 0-120%. The baseline first synthetic year fits four pressure quantiles; later dates and sensitivities use the frozen monotone response. Use `--calibration backend/data/validation/fill_qr/calibration.json` to reuse a fit with matching source/range/seed provenance. `--fit-end` explicitly overrides the fitting end date; the default is 2024-10-09 for this dataset. Do not refit on downstream validation/test dates. These are assumed ordinal frequencies, not measured Gaussian fullness.

Residential bins use existing allocation. Valid non-residential bins share 100 equivalent users per site and stream across categories. District normalization uses an explicit reviewed dictionary. Invalid inputs retain every row with both outputs NULL and an audit. Zero allocated residential exposure is retained, not imputed.

Uncapped source demand remains conserved and audited in m³; calibrated fullness is a nonlinear scenario response, not 100 times demand divided by capacity. It preserves order, accumulation, zero inflow and sampled residue. It does not solve source catchment errors or establish physical mass balance. Diagnostic excess source demand is not measured litter. See `docs/fill-qr-rule-changes.md` for every change.

`collected` and `retry_collected` are synthetic successful assessable visits. The first success anchors unknown initial fill; both outputs are NULL until the next day. Later fill targets occur before successful collection, with 10% adjacent-class noise. Other statuses have NULL fill labels and do not reset. `qr_alerts` counts reports through yesterday and resets the day after success; today's target/status/reports do not alter today's feature.

The existing calendar and registry/population snapshots are synthetic/static over three years. Events are disabled because no dated event input exists. Public holidays come from Lithuanian dates. No measured historical fill or trusted bulk density is available. Neither generated labels nor the 240 kg regional annual reference establish accuracy for real Vilnius bins.

SHA-256-derived independent random streams use IDs and the full date range. Processing whole bins in a different order does not change their values; changing the range changes the recorded configuration. Paired sensitivities reuse random draws, including Poisson inverse-CDF uniforms. Record package versions when reproducing outputs.

Diagnostics contain calibration, manifest, all exclusions/fallbacks, sampled complete pools, full verification, sensitivities, six charts and a realism report. Generated data/rules remain gitignored; scripts, tests and this guide are versioned. Validation compares every original field and independently reconstructs every known-day fullness and worker label using scalar cycle accumulation and an independently evaluated response. It checks masks, timing and sample reproducibility. Period distributions separate calibration from subsequent years. Sensitivity sampling includes extremes and is not an unbiased city-wide estimate. Do not test ordinal codes as continuous Gaussian observations.
