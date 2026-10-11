# Design

## Context

See proposal.md for motivation and the delta spec for behavior. `backend/app/ml/` is empty; existing CLI modules live under `app`. The 2.9 GB enriched CSV is sorted by bin then consecutive date, as verified across all rows. Real-history exports contain no fill measurements. Existing `bin_hist.fill_level` is observed data constrained to 0..3 and is not a prediction store.

## Goals / Non-Goals

**Goals:** A complete offline vertical slice, reusable loaded predictor, independently auditable data/time boundaries, feasible local model comparison and full-registry retrospective inference on 2026-09-15.

**Non-Goals:** New services, automatic training, VASA requests, rewriting generator data, simulator-state features, UI/API scope expansion, invented real fill measurements or confidence claims for unlabeled bins.

## Decisions

1. **Location and dependencies.** Implement `app.ml` with small stage entrypoints and shared feature/model contracts. Keep configuration in `backend/configs/ml.yaml`, optional pinned analysis dependencies separate from the application, and all large outputs under `backend/data/ml/`. This matches the existing backend rather than adding `src/` or another deployment.

2. **Availability contract.** Prediction describes an expected worker assessment before hypothetical service on D, using end-of-D-1 observations plus the date's deterministic calendar fields. Same-day raw safe QR/calendar counters are accepted only because the source implementations prove they exclude D. Same-day statuses/labels and all generator diagnostics are forbidden. Previous ratings are available the next day. Retrospective metrics can use source targets only after prediction.

3. **Memory-aware features.** Stream complete bin blocks from CSV, validate order/continuity, compute lag/rolling/expanding features before selecting labels, and write bounded Parquet row groups. Retain one bin across CSV chunk boundaries. Source hashes, feature schema/configuration and stage completion metadata invalidate stale caches. No full in-memory copy or global sort is needed for verified sorted input; unordered input fails actionably rather than silently changing history.

4. **Feature definitions.** Initial numeric fields: calendar weekday/week/month, capacity, resident factor, holiday and 28-day counters, QR. Initial categories: season, waste type, canonical sub-district and object group. Add days since prior success/attempt/rating, previous status/rating, successful collections in [D-7,D-1] and [D-90,D-1], missed collections in [D-90,D-1], and expanding prior-label mean/median/std. Include missingness indicators. No-history values remain missing. `bin_id`, `site_id` and `population_cell_id` are grouping keys, not primary model inputs. Site target aggregates and high-cardinality target encoding are excluded from the first model to avoid speculative complexity; native category handling, frequency encoding and fold-safe target encoding are discussed in documentation.

5. **Static normalization and quality.** Reuse the reviewed district alias data as a static input, not learned target information. Preserve unknown/ambiguous labels with explicit categories and flags. Capacity <=0 becomes missing only in model features; source zeros stay unchanged. Preserve zero QR/exposure. Merge registry-only bins with optional `bin_population.csv`, which covers all registry bins. Quality output uses a stable ordered list of issue codes, with `complete` for no issues and explicit multiple-issue representation.

6. **Temporal design.** Calibration/history: 2023-10-10..2024-10-09; train: 2024-10-10..2026-04-09; validation: 2026-04-10..2026-07-09; test: 2026-07-10..2026-10-09. Two expanding folds within train use date masks, never row positions. Past labels within validation/test can update strictly historical features, reflecting daily operational availability; they never fit preprocessing/models. The control date is 2026-09-15. All model fitting and parameter selection precede this date, and labels/outcomes on or after it cannot affect its features. Test-date distribution inspection is a data audit, not model selection.

7. **Sampling and resource pilot.** Seed 42. Use deterministic training-only date/class and waste/object-group/class marginal strata, preserving dates, classes and rare category combinations while permitting the smaller sample; record exact sampled keys and coverage rather than claim all-bin coverage. Full feature generation uses every training-period day. Start with a small pilot, measure duration/process RSS and available RAM, probe GPU separately, and propose explicit coarse/refined grids and sample limits before expensive work. One fit at a time, up to four CPU threads, ten-minute search budget for the user-requested reduced run. Approximately 8 GiB total RAM and 4 GiB GPU make a full Cartesian full-data grid unsuitable. The current final fit uses the user-requested 100,000-row bounded sample; record omitted rows and group coverage.

8. **Model-specific preprocessing.** Fit numerical medians and missing indicators on each fold's training rows. Use bounded one-hot categories for RF/XGBoost and native categorical strings for CatBoost; missing and unseen categories are supported. Do not scale trees. XGBoost uses five-class `multi:softprob` and histogram training; GPU is enabled only after a successful compatibility/memory probe. CatBoost uses multiclass loss and explicit bootstrap/weighting parameters. Fail an unusable training fold with missing target classes explicitly; map probabilities using saved `classes_` and validate all five columns.

   Pilot resolution: both libraries verified CUDA on the available GTX 1650 Ti. The active reduced run trains CatBoost only on GPU; RF/XGBoost implementations remain available but are not trained in this run. CatBoost is limited to half the GPU RAM. Persisted inference uses CPU. GPU reductions can vary between runs despite fixed seeds. Resource extrapolation uses warm fits after separate library/CUDA initialization. Identical feature content may be revalidated after model-only configuration changes; input/feature-code/Parquet hashes and feature-affecting settings must match.

9. **Search and selection.** Transparent custom temporal search, 4 coarse plus 4 refined candidates per CatBoost/RF model over two common folds (32 search fits), plus small pilots and two final refits. Explicit none/balanced weighting comparisons, early stopping inside training folds for boosting, fit durations, fold means/std and best parameters are saved. Pilot estimates determine the concrete proposal; execution requires confirmation. Final models fit train only, validation selects the primary model by combined classes-3/4 F1 with class-4 metrics disclosed, and test is evaluated once after freezing. Probability argmax is the decision rule; no forced proportions or unapproved threshold/calibration.

10. **Baselines and explanations.** Most-frequent and stratified dummy baselines are fitted on train; previous rating and prior bin median use available past labels, and waste/capacity/object-group medians use date-shifted group counts. Missing history uses a documented training-only prior. Save all comparison metrics, raw/normalized confusion tables, per-date/stream/capacity/input-quality errors, native and held-out permutation importance aggregated to original variables, bounded SHAP samples where feasible, class-4 and example explanations. SHAP feasibility must be reported explicitly rather than fabricated.

11. **Independent unseen-site evaluation.** Hold out a seeded 10% of sites, refit the selected configuration without those sites, and evaluate their later labeled rows separately. Use a cold-start representation with historical rating/collection/QR fields unavailable to represent registry-only deployment; report this additional assumption, held-out keys and exact sample sizes. This does not validate truly unlabeled bins.

12. **Inference and artifacts.** Serialize preprocessing and model together, with metadata/configuration/hashes/versions. Inference selects history strictly before D. For an existing retrospective D row, use only safe snapshot attributes/counters plus computed prior history; never its label/status. For future D after history ends, derive counters only where the observation window is complete; missing QR on a new date stays unknown except a known preceding success establishes reset zero. Missing days are not simulated. Registry-only bins receive static/calendar attributes and missing history. Compare control-date predictions to separately joined synthetic labels and report the labeled subset denominator.

## Risks / Trade-offs

- Synthetic labels and collection-day selection -> disclose that metrics do not establish real-world or unlabeled-day accuracy.
- Calibration-year dependence -> exclude that year from supervised fitting/evaluation, retaining historical context.
- Static registry/population snapshots and long 120% saturation -> report limitations and input-quality strata.
- Resource-dependent sampling -> pilot first, document coverage and obtain concrete search confirmation; never claim full-data training when sampled.
- History gaps or stale QR -> explicit missingness, no invented observations and focused as-of leakage checks.
- Disk/model size -> compressed Parquet, bounded depth/estimators, one active run directory and no redundant full CSV copies.

## Migration Plan

Create isolated code/configuration/docs, run the explicitly requested focused tests, validate sources, build deterministic caches and run a small pilot. Present its measured search budget for confirmation. After approved search/refits, freeze selection, evaluate test and unseen sites, reload the saved primary model and produce all 21,951 control-date predictions plus synthetic comparison. Hash raw inputs again to prove preservation. Existing application startup and database contracts remain unchanged; rollback is removing the optional ML files and ignored run directory.

User scope revision (2026-10-10): only CatBoost with hyperparameter search and smaller data, replacing the initial three-model run. Concrete conservative limits: 2,000-row pilot, 10,000 tuning rows, 50,000 final rows, two temporal folds, 16 search fits, 600 seconds of search, 2.5 GiB process RSS and 50% GPU RAM. The direct user instruction authorizes this reduced run; preserve it alongside the measured proposal. Marginal strata replace full joint strata because 49,679 full joint strata cannot fit a 10,000-row sample.

## Operational priority revision (2026-10-10)

The user removes historical_fill_mean, historical_fill_median and historical_fill_std, doubles the final sample to 100,000 rows,
and prioritizes classes 3 and 4 together. Double tuning to 20,000 rows, retain
CatBoost GPU / Random Forest CPU 32-fit search and the existing 600-second/2.5-GiB limits.
Persist selected original features in each bundle; excluded variables and their
missingness indicators cannot enter fitting, inference or importance. Cached
engineered columns may remain available for baseline/audit use.
Search primary score is binary F1 for target fill_level >=3 using P(3)+P(4)>=0.5.
Select the operational threshold on validation F1 only, with a fixed 0.05..0.95
step-0.05 grid and ties preferring proximity to 0.5. Freeze it before comparative
test and retrospective inference. Keep five-class argmax predictions alongside
separate needs_collection_probability and needs_collection outputs. Disclose
both the operational scores and secondary multiclass scores.
Preserve the initial run in its original directory; the revision uses a new run
directory. Sources and feature construction are unchanged, allowing checksum-
verified cache reuse. The test period and site-holdout diagnostics have already
been observed in the first run: these are repeated comparative evaluations,
not a new independent untouched holdout. No thresholds/parameters use test labels.

Latest clarification: exclude exactly historical_fill_mean, historical_fill_median and historical_fill_std; retain previous_worker_rating and days_since_previous_worker_rating. Train CatBoost and Random Forest for comparison, each with 4 coarse + 4 refined candidates over two folds (32 search fits total) and a 100,000-row final sample. Produce model-comparison charts emphasizing combined classes 3/4 precision, recall and F1. Prior CatBoost-only limits describe the superseded first run.
