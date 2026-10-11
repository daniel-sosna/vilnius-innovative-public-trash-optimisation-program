# Proposal

## Why

The collection plan is built from a mock prediction (uniform random levels seeded from the date), so the plan, and any routing built on it, reflects no real signal. The trained next-day fill predictor in `viptop_fill` already exists and is specified by `daily-fill-prediction`. Connecting it makes the main end-to-end workflow use the primary ML approach.

## What Changes

- `predict_fill_levels` runs the trained predictor (`viptop_fill`) instead of the mock, keeping the `{bin_id: level}` contract so plan building, storage and reading are unchanged.
- The prediction reads the enriched daily history CSV, the bin registry CSV, the population CSV and the delivered model `product/` from `VIPTOP_DATA_DIR`. If the history CSV or the product is missing, the command fails with an actionable error (for example "Historical data is not present in the system") and changes nothing.
- **BREAKING**: `--date` on `python -m app.interfaces.collection_plan` becomes required and means "today" T. T must be in 2026-09-01..2026-09-30; the plan is stored under T+1, the day the levels are predicted for. Other dates are rejected with a message that only September is available for simulation. The default of "today" is removed.
- Bins without a prediction are left out of the plan. Predictions for bins not stored in the database are ignored.
- The model runs before the database transaction opens, so a long scan does not hold locks.
- The backend image gains the inference dependencies (pandas, numpy, scikit-learn, catboost, joblib) and the `viptop_fill` package. No training code or research dependencies are added.
- The command summary reports the model as the prediction source, no longer "mock".

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `collection-plan`: the prediction requirement becomes model-based (September simulation window, T to T+1 date semantics, missing-input failures, skipped and ignored bins); the rebuild command requires `--date`; the summary names the model as the source.

## Impact

- Code: `backend/app/ml/fill_prediction.py`, `backend/app/services/collection_plan.py` (prediction before the transaction, skip bins without a level), `backend/app/interfaces/collection_plan/cli.py`, `backend/viptop_fill/` (no behavioural change), `backend/pyproject.toml`, `backend/uv.lock`, `backend/Dockerfile`.
- Docs: `docs/data/collection-plan.md`, `docs/data/fill-prediction.md`, `README.md` (pipeline row and overview wording).
- Data: relies on `VIPTOP_DATA_DIR` holding the enriched daily CSV, the bins export, `bin_population.csv` and the delivered model; none are in git.

## Uncertainties and assumptions

- **Runtime.** The docs report a scan of roughly 4-5 minutes per run on the development machine, not measured here. A slow run is accepted.
- **Synthetic history.** The CSV labels and the model's targets are synthetic assessments, not measured fill; plan quality inherits this. The prediction is for simulation in September 2026 only.
- **Registry mismatch.** The CSV registry may differ from the stored bins; the database defines which bins appear in the plan.
- **File names.** The CSV and product locations inside `VIPTOP_DATA_DIR` are fixed conventions (see design).
