# Proposal

## Why

The existing ML experiments need to become a developer-ready next-day predictor for the September 2026 demo. Both candidate models must be trained strictly before September, with one selected product model, consistent in-memory feature construction and only the current experiment's artifacts retained.

## What Changes

- Keep `backend/data/bin_days_20231010_20261009_enriched.csv` immutable as the current historical source. Retain the authoritative registry, population snapshot and reviewed district aliases. Database ingestion, database reads and demo UI integration are outside this change.
- Compare CatBoost and Random Forest with the same 21 active model inputs, 20,000-row tuning samples, 100,000-row final samples, two temporal folds and the existing bounded coarse/refined search. Prioritize combined classes-3/4 F1 and retain the full multiclass analysis.
- Select parameters, operational thresholds and the winning algorithm using only dates before 2026-09-01. Use August for model selection; refit both frozen candidates on deterministic samples drawn through 2026-08-31 inclusive. Evaluate the final models on the September demo scenarios without changing their selection.
- Define selected demo date T as the end of "today" and forecast date D as T+1. Historical outcomes may include T. Preserve the user-approved use of the four safe source counters from the D row, which already exclude D; never use D's fill assessment or collection outcome. Compute the eight added inputs in memory immediately before prediction.
- **BREAKING:** Expose a product entrypoint accepting history/registry DataFrames and explicitly supplied safe forecast-day counters, returning exactly `bin_id` and predicted `fill_level` in 0..4. Keep probabilities, operational decisions and evaluation details in research outputs rather than the product response. Runtime inference must not persist feature DataFrames or predictions implicitly.
- Deliver the selected model and its fitted preprocessing, feature-construction script, CPU inference example, pinned runtime dependencies, metadata and developer instructions. Keep both current candidate bundles and their analysis within the current run for comparison.
- Produce the same categories of EDA, metrics, confusion matrices, errors, explanations, unseen-site diagnostics and comparison charts as the current pipeline. Document only the active input contract in current code/configuration and delivery documentation.
- After the new run and product package pass verification, remove `backend/data/ml/fill-classifier/` and `backend/data/ml/fill-classifier-priority34-100k/`. Retain the immutable inputs, shared ML environment, unrelated data-generation work and this run's reproducibility artifacts.

## Capabilities

### New Capabilities

- `daily-fill-prediction`: Next-day container fill forecasting, pre-September temporal model selection, current-run comparison, in-memory inference and developer delivery.

This preserves the capability path used by the implemented but unarchived `train-fill-classifier` change; no durable ML spec currently exists under `openspec/specs/`. The new contract supersedes that experiment's dates, runtime output/cache contract and instruction to preserve old runs. Automatic archiving or rewriting the prior change is outside this proposal; the overlapping deltas must be reconciled before eventual archive.

### Modified Capabilities

None. Existing registry, stored calendar, observed collection and resident-request contracts are unchanged.

## Impact

Update `backend/app/ml/`, `backend/configs/ml.yaml`, `README_ML.md` and relevant existing ML checks. Use `backend/data/ml/september-fill-predictor/` for this run, with a self-contained `product/` directory. Reuse the existing optional Python environment and model libraries; introduce no service or database dependency. Source adapters remain separate from the DataFrame-based predictor so developers can later provide database-loaded frames.

Key limitations: labels are synthetic and available mainly on successful collection days; September dates were inspected in previous experiments and are comparative rather than a previously untouched holdout; current registry attributes are static snapshots; bins without rating history have previously shown weak performance. Product output is five-class probability argmax, while the separately reported urgent decision uses the frozen P(3)+P(4) threshold; report both urgent scoring rules so app behavior is measurable. For T=2026-09-30, D=2026-10-01 is a valid next-day forecast and part of demo evaluation.
