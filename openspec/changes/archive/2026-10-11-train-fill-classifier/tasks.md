# Tasks

## 1. Configuration and input validation

- [x] 1.1 Add optional pinned ML dependencies, configuration and stage entrypoints under `backend/app/ml/`; verify an isolated Python 3.12 environment installs them and every command has actionable `--help` without loading database settings. Document setup and project-relative paths in `README_ML.md`.
- [x] 1.2 Implement memory-bounded data validation and verified dictionaries for daily history, authoritative registry and optional population snapshot; run the full source checks and save hashes, row/date/bin/site counts, missingness, target/status/QR distributions, duplicate/continuity/domain checks, exclusions, label availability, category drift and split summaries. Verify the known 23,777,720/21,695/21,951 counts and add the requested schema/duplicate/zero-versus-NULL tests.

## 2. Historical features and complete-registry inputs

- [x] 2.1 Implement complete-bin streaming lag/rolling/expanding features and bounded Parquet caching with source/configuration provenance; verify same-day/future perturbation tests, bin and chunk boundaries, source counter timing, chronological split boundaries and label filtering after feature generation. Save the full feature dictionary with definition, source, window, leakage boundary, missing meaning and registry-only inference availability; document feature commands.
- [x] 2.2 Build authoritative-registry as-of-date feature rows and ordered input-quality flags, including no history/no prior labels, missing QR/object group, ambiguous district and invalid capacity; verify 21,951 unique rows on 2026-09-15, optional population coverage, known-reset versus unknown future QR, and no use of current-day labels/status. Save registry coverage and quality tables, and document inference semantics.
- [x] 2.3 Produce concise EDA and source tables for target/date/waste/capacity/district/object-group distributions, label availability/counts, zero-label bins/sites, QR zeros/missingness and target association, statuses, collection intervals and feature drift. Verify each important chart has its underlying table and temporal labels.

## 3. Models, baselines and a measured search proposal

- [x] 3.1 Implement fold-fitted model-specific preprocessing and independently reloadable RF/XGBoost/CatBoost bundles, fixed five-class probability mapping and configurable seeds; implement all five chronological baselines with explicit training-only fallback priors. Verify missing/unseen categories, valid probabilities, missing-class fold handling and focused reload/inference tests; document category/identifier/encoding choices.
- [x] 3.2 Build deterministic training-only stratified tuning/final samples, two common expanding temporal folds, transparent coarse/refined grids, weighting experiments, fold means/std, early stopping and duration/resource logging. Run a small CatBoost resource pilot and GPU compatibility probe; publish exact keys/coverage, proposed grids/combinations/fits and measured time/memory estimates. Obtain explicit confirmation of the concrete search configuration before expensive tuning; keep the approval and configuration together in the run metadata.

## 4. Approved training and evaluation

- [x] 4.1 Execute the approved coarse/refined search and a final CatBoost refit on the user-requested reduced documented training sample; save complete search results, selected parameters, preprocessing/models, package versions, logs and validation predictions. Verify every fit date precedes validation/control dates and sample provenance is reproducible.
- [x] 4.2 Compare the configured model and all baselines on validation using Macro F1, weighted F1, balanced accuracy, accuracy, per-class precision/recall/F1, class-4 precision/recall, raw/normalized confusion matrices, log loss, ordinal MAE, quadratic kappa, severe-error rate and classes-3/4 operational precision/recall/F1; freeze model selection and argmax rule, then evaluate untouched test once. Save prediction/metric/comparison tables and the requested metric, distribution, error-by-date/waste/capacity/quality and training-time charts; verify each chart's source table and document denominators/limitations.
- [x] 4.3 Refit the selected configuration on training sites excluding a seeded 10% site holdout and evaluate held-out later rows with the documented cold-start history mask; save held-out IDs, sample sizes, metrics and coverage separately from chronological evaluation. Verify no held-out-site labels fit preprocessing or the model and document what this does and does not measure.
- [x] 4.4 Generate native and held-out permutation importance for the configured CatBoost model, aggregate transformed levels to original variables, and perform bounded SHAP where feasible; save top 15-25 tables/charts, correlated-feature notes, selected-model class-4/global/example explanations and a short presentation explanation. Verify held-out sampling and clearly record any measured SHAP resource limitation without causal claims.

## 5. Retrospective inference and delivery verification

- [x] 5.1 Reload the primary model in a fresh process and predict every authoritative registry bin for 2026-09-15; save all five probabilities, input-quality flags and a separate comparison with available same-day synthetic targets. Verify exactly 21,951 unique IDs, no missing predictions/probabilities, integer classes 0..4, probability sums/ranges and no duplicate bin/date keys; report labeled comparison size and quality-group distribution.
- [x] 5.2 Run the requested focused tests and integration commands, recheck source hashes and assemble the final English ML report and `README_ML.md` with actual splits/features/grids/fits/parameters/baseline and model metrics/class-4 and ordinal results/importance/coverage/runtime/artifact paths. Verify documentation includes generator calibration, collection-day label selection, unknown unlabeled-bin accuracy, static snapshots, long saturation, absent real measurements and coverage-versus-confidence limitations; run strict OpenSpec validation and leave the change available for review.

## Workflow follow-up

- Archive only when the user requests it after implementation and review.

User scope revision (2026-10-10): only CatBoost with hyperparameter search and smaller data, replacing the initial three-model run. Concrete conservative limits: 2,000-row pilot, 10,000 tuning rows, 50,000 final rows, two temporal folds, 16 search fits, 600 seconds of search, 2.5 GiB process RSS and 50% GPU RAM. The direct user instruction authorizes this reduced run; preserve it alongside the measured proposal. Marginal strata replace full joint strata because 49,679 full joint strata cannot fit a 10,000-row sample.

## 6. Operational classes 3/4 revision

- [x] 6.1 Add persisted model feature exclusions, remove historical_fill_mean/median/std, double tuning/final samples to 20,000/100,000 rows, and implement probability-sum classes-3/4 F1 search plus validation-only threshold selection. Verify exclusion survives reload and metrics/decisions match the binary target; preserve the prior run and revalidate copied caches.
- [x] 6.2 Execute the authorized CatBoost/RF pilot, 32-fit search and final fit; freeze the operational decision on validation, then run comparative test/control-date evaluation and unseen-site cold start. Save probabilities, group precision/recall/F1, complete-registry predictions, threshold curve and exact sample/approval metadata.
- [x] 6.3 Refresh original-variable importance, bounded SHAP, comparative report, README and charts; verify source preservation, all 21,951 prediction rows, focused tests and strict OpenSpec validation. Clearly disclose repeated use of the same test period and historical-label availability limitations.

Latest clarification: exclude exactly historical_fill_mean, historical_fill_median and historical_fill_std; retain previous_worker_rating and days_since_previous_worker_rating. Train CatBoost and Random Forest for comparison, each with 4 coarse + 4 refined candidates over two folds (32 search fits total) and a 100,000-row final sample. Produce model-comparison charts emphasizing combined classes 3/4 precision, recall and F1. Prior CatBoost-only limits describe the superseded first run.
