# Design

## Context

`build_plan` calls `predict_fill_levels(session, day)` and stores the result in `bin_fill`; plan tables and the read API depend only on its `{bin_id: level}` contract (see proposal.md for motivation). The trained predictor is the standalone package `viptop_fill`. `viptop_fill.csv_demo.predict_csv(product, daily_csv, registry_df, today, population_df)` already computes the prediction for every registry bin for `today + 1` from CSV files, and is what `app.ml.predict` calls.

Constraints:
- The database has no synthetic `fill_level` or `qr_alerts` history, so the model cannot be fed from the database. The enriched daily CSV is the only source.
- The backend image currently copies only `app/` and installs no ML dependencies; `viptop_fill` is not in the image.
- Data files live in `VIPTOP_DATA_DIR` (`app.core.config.data_dir()`, mounted at `/app/data` in the container).
- The model's validated window is T in 2026-09-01..09-30 (`daily-fill-prediction`).

## Goals / Non-Goals

**Goals:**
- Replace the mock behind the unchanged contract, with the model run live from the CSV.
- Fail early and clearly when inputs are missing or the date is outside the window.
- Keep long model runs out of the database transaction.

**Non-Goals:**
- No speed-up of the CSV scan, no caching or storing of predictions.
- No training, evaluation or packaging changes; no change to `viptop_fill` behaviour.
- No new API endpoint, table or UI.
- No prediction outside September 2026.

## Decisions

**1. Inputs from fixed names in `data_dir()`.** The CSV paths and the model location are conventions, not new settings:

| Input | Location under the data directory |
|---|---|
| Daily history | the single `bin_days_*_enriched.csv` |
| Bin registry | the `bins_<digits>.csv` with the highest number |
| Population | `bin_population.csv` |
| Model | `ml/september-fill-predictor/product/` |

These match `backend/configs/ml.yaml`, so the output of `app.ml.run` is usable without copying. A pattern with no match, or several matches for the daily file, is a missing-input error. *Alternative:* new environment variables per file; rejected as more configuration for a fixed demo dataset.

**2. Live inference through `predict_csv`.** `predict_fill_levels` loads the registry and population CSVs, calls `predict_csv(product, daily, registry, T, population)` and returns `{bin_id: level}`. *Alternatives:* precomputed predictions loaded into a table (needs a second command and stored state; the team chose live); building features from the database (history labels do not exist there).

**3. Prediction before the transaction.** The service obtains the levels first and passes them to the transactional part, so `SET LOCAL lock_timeout` and the transaction start only after the scan. Contract: `predict_fill_levels(day)` no longer takes a session, since the database is not an input; callers pass the plan date `T+1`, and the function derives `T = day - 1`. Both `build_plan` and the CLI are its only callers.

**4. Date handling lives in the CLI and prediction function.** The CLI takes required `--date T`. The prediction function validates `T` in 2026-09-01..09-30 and raises an error naming the September-only limit. The plan is stored under `T+1`. The function owns the window, because it is the model's validity limit.

**5. Gaps are handled at the join.** Levels are filtered to stored bin IDs before insertion into `bin_fill` (ignored extras); stored bins absent from the levels never enter `bin_fill`, so they are not due and appear in no stop. `PlanSummary.evaluated` counts bins with levels. *Alternative:* fail on any mismatch; rejected by the team.

**6. Backend dependencies.** Add `numpy`, `pandas`, `scikit-learn`, `catboost` and `joblib` to `backend/pyproject.toml`, pinned to the versions in `backend/requirements-ml.txt` so the delivered model loads identically, and update `uv.lock`. `holidays` is already present. The Dockerfile copies `viptop_fill/` next to `app/`, and `viptop_fill` must be importable from the working directory. Training-only packages (scipy extras, shap, matplotlib, psutil) are not added. No separate service or deployment is introduced.

**7. Shared contract changes.**
- `predict_fill_levels` signature changes (see 3).
- The CLI's `--date` becomes required.
- The plan date stored is `T+1`.
- Affected components: `collection_plan` service and CLI, and future routing, which reads the plan by date through `get_plan` (unchanged).

## Risks / Trade-offs

- [Long run, about 4-5 minutes by the docs, unmeasured] → accepted by the team; output states progress at start; prediction runs outside the transaction.
- [Heavier backend image from the ML libraries] → inference-only dependencies, pinned versions; no GPU libraries are needed for CPU inference.
- [Version drift breaks model loading] → pins equal the training environment; the model schema check in `FillPredictor` fails loudly.
- [CSV registry differs from stored bins] → the database governs; extras ignored, missing skipped; both counts are logged.
- [Synthetic labels] → documented as an assumption in the docs and summary.
- [Large CSV missing in a fresh worktree] → clear failure, per the repository rule that data is added by the developer.

## Migration Plan

1. Rebuild the backend image after the dependency change.
2. Place the CSVs and the model product in the data directory.
3. Rebuild plans with the new command. Plans built earlier with mock levels remain in the database until a date is rebuilt; plan dates outside September 2026 cannot be rebuilt.

Rollback: restore the previous `predict_fill_levels` and CLI from git; no schema change is involved.
