# Tasks

## 1. Backend runtime

- [x] 1.1 Add `numpy`, `pandas`, `scikit-learn`, `catboost` and `joblib` to `backend/pyproject.toml`, pinned to the versions in `backend/requirements-ml.txt`, and refresh `backend/uv.lock`. Verify: `uv sync --locked` succeeds and `uv run python -c "import viptop_fill, catboost, pandas"` runs from `backend/`.
- [x] 1.2 Copy `viptop_fill/` into the image in `backend/Dockerfile` so it is importable next to `app/`. Verify: `docker compose build backend` succeeds and `docker compose exec backend uv run python -c "import viptop_fill"` exits 0.

## 2. Prediction from the model

- [x] 2.1 Rewrite `predict_fill_levels` in `backend/app/ml/fill_prediction.py` to take the plan date, resolve the history CSV, registry CSV, population CSV and `ml/september-fill-predictor/product/` under `data_dir()`, call `predict_csv` for `T = day - 1`, and return `{bin_id: level}`. Raise clear errors for missing inputs ("Historical data is not present in the system", model missing) and for `T` outside 2026-09-01..09-30 (only September is available for simulation). Update the docstring to describe the model and its synthetic-history assumption. Verify: calling it with a date outside September, and with the history CSV renamed, raises the expected messages before any scan starts.
- [x] 2.2 In `backend/app/services/collection_plan.py`, obtain the levels before opening the transaction, drop levels for bin IDs not stored, and let stored bins without a level stay out of `bin_fill`. `evaluated` counts bins with a level. Verify: with a stored bin removed from the predictions, the build succeeds and that bin is in no stop; with an extra predicted ID, it is ignored.

## 3. Command

- [x] 3.1 In `backend/app/interfaces/collection_plan/cli.py`, make `--date` required (T), reject dates outside September 2026 with the September-only message, build and store the plan under `T+1`, and replace the "MOCK" summary text with the model source and the synthetic-history note. Print the given date and the plan date. Verify: `docker compose exec backend uv run python -m app.interfaces.collection_plan` without `--date` exits 1; `--date 2026-10-11` exits 1 with the September message; invalid and missing-input cases exit 1 and leave `collection_stops` unchanged.

## 4. End-to-end check

- [ ] 4.1 With the CSVs and the model product in `VIPTOP_DATA_DIR` (ask the developer if any is missing, per AGENTS.md), run `docker compose exec backend uv run python -m app.interfaces.collection_plan --date 2026-09-15` and check the summary (exit 0, evaluated and due counts plausible) and that `collection_stops` has rows for 2026-09-16 and none new for 2026-09-15. Rerun with `--threshold 3` and confirm 2026-09-16 shrinks and 2026-09-17 is untouched. Record the observed run time and counts in `openspec/changes/use-real-prediction-data/verification.md`.

## 5. Documentation

- [ ] 5.1 Update `docs/data/collection-plan.md`: replace the "Mock prediction" assumption with the model source, synthetic history, the data-directory inputs and the `ml/september-fill-predictor/product/` location, the required `--date` (T, September 2026, plan stored under T+1), the missing-input failures, and the observed run time. Remove "mock" wording and the default-today row.
- [x] 5.2 Update `docs/data/fill-prediction.md` to point to the collection plan as the in-product consumer instead of "uses its own mock provider", and `README.md` (overview sentence, pipeline row 4 and the `ml/` structure comment) to drop "mock". Verify: `grep -ni mock README.md docs/data/collection-plan.md docs/data/fill-prediction.md` finds no stale prediction wording.
