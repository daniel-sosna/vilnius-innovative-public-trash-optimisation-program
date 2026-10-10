# Tasks

## 1. Active features and in-memory next-day inputs

- [x] 1.1 Extract an IO-independent feature builder with the 21 active inputs and eight historical calculations; keep identifiers/quality fields separate and retain previous assessment/age. Verify existing history-boundary, zero-versus-missing and category checks, and publish the active feature dictionary without per-bin feature caches.
- [x] 1.2 Implement the T -> D=T+1 DataFrame contract with history through T inclusive, D calendar fields and separately supplied D-keyed safe counters. Verify the 2026-09-15 -> 2026-09-16 and 2026-09-30 -> 2026-10-01 cases, unchanged supplied counters, caller-frame immutability and invariance to D/later outcomes; document the allowed input fields and timing.
- [x] 1.3 Add the bounded CSV adapter using complete-bin batches and an allowlist for D counters; adapt training/evaluation sampling to streamed in-memory features and remove dependence on persisted feature snapshots. Verify batch/chunk consistency, duplicate/continuity errors and a small end-to-end dry run that creates no constructed-feature files; document memory and missing-counter behavior.

## 2. Temporal configuration and reproducible search

- [x] 2.1 Configure the new run root, selection-stage training through 2026-07-31, August validation, final fitting through 2026-08-31, existing two folds and all 30 demo today/target pairs. Verify date-boundary checks reject September fitting/selection and keep calibration history out of supervised samples; update the corresponding commands and period table in README_ML.md.
- [x] 2.2 Generate and record deterministic 20,000-row tuning, 100,000-row selection-fit and 100,000-row final-fit sample keys with date/class/category/bin/site coverage; verify both candidates share appropriate keys and every supervised row respects its stage's boundaries. Preserve source hashes and sample provenance without saving engineered feature values.
- [x] 2.3 Run the bounded two-model resource pilot and GPU probe, then save the concrete proposal and user authorization for this run's configuration. Verify accounting for 32 search fits, two selection fits, two final fits and one cold-start refit, with the existing search/RSS/GPU limits; document measured estimates and fail explicitly if those limits are infeasible.
- [x] 2.4 Execute the four-coarse/four-refined common-fold search for CatBoost and RF; verify all 32 fit records, no August/September selection leakage inside folds, complete score/parameter/runtime logs and a non-successful exit for resource-limit failures. Save chosen hyperparameters and effective iteration counts with reproducible metadata.

## 3. August selection and frozen final models

- [x] 3.1 Fit the two selection-stage models, compare them and active-input baselines on August, and freeze the winning algorithm and each probability-sum threshold. Verify threshold-grid provenance, no September/October labels in selection, valid class mapping and separate probability-sum/grouped-argmax urgent scores; document selection-stage results and decision rules.
- [x] 3.2 Refit both candidates on the common 100,000-row final pre-September sample using frozen parameters/iterations and train-only preprocessing. Verify saved/reloaded probabilities, no overlapping early-stopping evaluation set, fitting cutoff, resource limits and separate selection/final metadata; save only the current final candidate bundles and document the refit stage.
- [x] 3.3 Expose the selected-model next-day predictor returning exactly bin_id and integer fill_level without implicit writes or backend/database imports. Verify missing/unseen categories, generic caller-registry IDs, current 21,951-bin coverage and input immutability; document the minimal product response and its argmax semantics.

## 4. Comparative analysis and explanations

- [x] 4.1 Produce both final models' predictions for all 30 September today selections and next-day targets, joining synthetic labels only after prediction. Verify per-date uniqueness/registry coverage, pooled and daily labeled denominators, separation from August model selection and both urgent scoring rules; publish prediction/metric tables and the two-model comparison charts.
- [x] 4.2 Refresh EDA, active-input baseline comparisons, per-class metrics, confusion matrices, ordinal/severe errors, date/waste/capacity/quality analyses and runtime charts. Verify every chart has a source table and the report identifies synthetic labels, static snapshots, collection-day selection and previously inspected evaluation dates.
- [x] 4.3 Run the separate seeded 10% unseen-site cold-start diagnostic with a selected-configuration pre-September refit excluding held-out sites. Verify site disjointness, history masking and exact sample/denominator metadata; add its metrics and limitations to the report without changing the frozen winner.
- [x] 4.4 Refresh native and 500-row permutation importance plus feasible 50-row SHAP for both candidates using the active schema. Verify feature-name/order consistency, post-training sample provenance and chart tables; document resource limitations, correlated inputs and selected-model examples without saving constructed feature DataFrames.

## 5. Standalone developer package

- [x] 5.1 Export only the selected final candidate with fitted preprocessing into product/model.joblib using a portable library-object payload; include the shared viptop_fill feature/runtime source, normalization data, manifest, active schema and pinned CPU dependencies. Verify source/model hashes, absence of custom app.ml pickle dependencies and independence from the losing candidate/research caches.
- [x] 5.2 Deliver an English developer README, minimal DataFrame example and bounded CSV demo adapter with explicit today/date/counter semantics and no database connector. Verify the documented invocation returns exactly the two requested columns, preserves caller data and creates no implicit feature/prediction files.
- [x] 5.3 Copy the product package to an isolated temporary location and run a fresh CPU process with the repository removed from the import path. Verify output equality with the selected final research model, valid probabilities internally, unknown-category/no-history behavior and successful mid-/end-September date examples; save a repeatable verification command and concise result record in the current run.

## 6. Replacement verification and cleanup

- [x] 6.1 Run the existing adapted focused ML checks and integrated current-run verification, including all 30 date mappings, source hashes, sample/selection boundaries, chart/table completeness, active-schema consistency and isolated package prediction. Verify all checks pass and publish the complete current English report before deleting any prior run.
- [x] 6.2 Resolve and verify the two explicitly allowlisted superseded run directories are ordinary immediate children of backend/data/ml, then remove them with native PowerShell LiteralPath operations. Verify immutable inputs, .venv, unrelated work and the current run remain; record cleanup and update current documentation so it references only the delivered run/schema.
- [x] 6.3 Repeat the isolated product prediction and source-hash checks after cleanup, verify both old run directories are absent and no product/report dependency resolves to them, and run strict OpenSpec validation. Publish final delivery paths and verification results with both current comparison models retained in research and one winner in the developer package.

## Workflow follow-up

- Implementation begins only through the apply workflow after this proposal is presented.
- Archive reconciliation (2026-10-11, explicitly requested by the user): retain train-fill-classifier as superseded history without syncing its obsolete delta, and sync this change's complete current daily-fill-prediction contract to main specs. See ARCHIVE_NOTES.md in both changes for the decision and verification evidence.
