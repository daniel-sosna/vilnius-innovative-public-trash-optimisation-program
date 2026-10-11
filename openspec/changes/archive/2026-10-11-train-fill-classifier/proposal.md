# Proposal

## Why

The enriched three-year CSV has synthetic worker ratings but the application has no reproducible predictor. We need a measurable five-class model and complete-registry retrospective predictions without turning predictions into observations or using future outcomes.

## What Changes

- Add offline validation, feature generation, temporal tuning, training, evaluation and inference commands under `backend/app/ml/`, with configuration and independently reloadable model bundles.
- Compare five historical/dummy baselines, CatBoost and Random Forest; select one primary model by combined classes-3/4 F1 and report class-4, operational and ordinal metrics, explanations and input-quality coverage.
- Build strictly historical features before selecting labeled days, retaining genuine zeros and unknown history. Produce exactly one probability-bearing prediction per registered bin, including bins with invalid inputs or no history.
- Use the first synthetic year only as generator calibration/history. Train on 2024-10-10..2026-04-09, validate on 2026-04-10..2026-07-09 and test on 2026-07-10..2026-10-09. The user-confirmed demonstration date is **2026-09-15**, compared with available synthetic labels, using a model fitted before that date.
- Add the explicitly requested focused tests, reproducibility documentation, source tables, charts, manifests and a final ML report. Perform a small resource pilot and obtain confirmation of the concrete search budget before expensive tuning.

## Capabilities

### New Capabilities

- `daily-fill-prediction`: Reproducible, explainable daily five-class prediction and temporal evaluation over the authoritative container registry.

### Modified Capabilities

None. Existing observed history, registry, calendar, resident-request and browsing contracts remain unchanged.

## Impact

Python ML dependencies are optional and isolated from the running backend. Code/configuration/docs are versioned; large datasets, caches, models and reports remain under ignored `backend/data/ml/`. No VASA synchronization, new deployment, database migration or automatic application-startup training is needed. Downstream optimisation can consume the separate prediction schema and Python loader.

Verified inputs: 23,777,720 daily rows, 21,695 bins, 6,816,901 labels and 21,951 registry bins. There are 256 registry-only bins and 1,136 daily-history bins without labels. All real-history fill measurements are NULL; the user explicitly accepted synthetic retrospective comparison. Material risks are label selection on successful collection days, generator calibration, static snapshots, missing inference history and the laptop's approximately 8 GiB RAM/4 GiB GPU. Full-data final fitting is resource-dependent; sampling must be deterministic, recorded and preserve training-period strata. Predictive accuracy on unobserved days and real operations remains unverified.

User scope revision (2026-10-10): only CatBoost with hyperparameter search and smaller data, replacing the initial three-model run. Concrete conservative limits: 2,000-row pilot, 10,000 tuning rows, 50,000 final rows, two temporal folds, 16 search fits, 600 seconds of search, 2.5 GiB process RSS and 50% GPU RAM. The direct user instruction authorizes this reduced run; preserve it alongside the measured proposal. Marginal strata replace full joint strata because 49,679 full joint strata cannot fit a 10,000-row sample.

Current user-authorized revision: exclude historical_fill_mean, historical_fill_median and historical_fill_std, compare CatBoost with Random Forest, and double final/tuning data to 100,000/20,000 rows, and prioritize binary F1 for classes 3 and 4 together using their summed probability and a validation-selected threshold. Preserve and compare the initial run; retain five-class output and explicit repeated-test limitations.

Latest clarification: exclude exactly historical_fill_mean, historical_fill_median and historical_fill_std; retain previous_worker_rating and days_since_previous_worker_rating. Train CatBoost and Random Forest for comparison, each with 4 coarse + 4 refined candidates over two folds (32 search fits total) and a 100,000-row final sample. Produce model-comparison charts emphasizing combined classes 3/4 precision, recall and F1. Prior CatBoost-only limits describe the superseded first run.
