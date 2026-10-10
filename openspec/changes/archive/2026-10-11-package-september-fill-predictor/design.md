# Design

## Context

See `proposal.md` for the outcome and scope. The implemented `train-fill-classifier` pipeline already supports the two candidates, chronological search, probability mapping, validation-only operational thresholds, diagnostics and reports. Its current configuration fits through April, selects through July and evaluates through October. Feature generation and inference currently depend on persisted Parquet feature caches, and the public prediction command writes a rich research result.

The reusable logic is in `backend/app/ml/features.py`, `modeling.py`, `search.py`, `evaluation.py`, `explanations.py` and `reporting.py`. Existing focused checks cover history boundaries, source-counter timing, missingness, reload and registry coverage. The current environment and raw exports are available. ML has no durable main spec yet; this change reuses the existing delta's `daily-fill-prediction` capability path rather than inventing a parallel capability.

Design is warranted because chronological selection/refitting, memory-bounded feature generation and a standalone inference package cross several existing modules.

## Goals / Non-Goals

**Goals:** Separate data acquisition, pure feature construction, model execution and research output. Use the same active schema and time semantics everywhere. Make a copied product package runnable on CPU with caller-supplied DataFrames, independently of research folders and backend database settings.

**Non-Goals:** Database ingestion or queries, new migrations/services, demo UI changes, source-data regeneration, full-data model fitting, new prediction algorithms, or automatic OpenSpec archive. Existing checks can be adapted; verification also exposes a repeatable standalone command rather than introducing an additional test framework.

## Decisions

### 1. Use a fixed cutoff and separate selection from delivery refits

Use the following explicit target-date periods:

| Stage | Dates | Purpose |
|---|---|---|
| Generator calibration/history | 2023-10-10..2024-10-09 | Historical context only |
| Selection-stage fitting | 2024-10-10..2026-07-31 | Search and fit each comparison candidate |
| Model/threshold selection | 2026-08-01..2026-08-31 | Compare selection-stage models and freeze decisions |
| Final fitting | 2024-10-10..2026-08-31 | Refit both frozen candidates for delivery/comparison |
| Selected demo "today" | 2026-09-01..2026-09-30 | End of available observation day T |
| Demo forecast targets | 2026-09-02..2026-10-01 | Next-day comparative evaluation |

Retain the two existing temporal search folds: train 2024-10-10..2025-10-09 / validate 2025-10-10..2026-01-09; train 2024-10-10..2026-01-09 / validate 2026-01-10..2026-04-09. They fit entirely inside the selection-stage training period.

Selection-stage fitting uses a 100,000-row deterministic sample. August selects each probability-sum threshold and the algorithm; freeze its parameters, effective boosting iteration count and decision rules. Final fitting draws a common deterministic 100,000-row sample from the enlarged pre-September period, with both candidates using the same keys. Do not promise that the smaller-period sample is nested: period coverage and sample reproducibility are the requirements. Final fitting uses no early-stopping evaluation set from September or from the overlapping August fitting rows.

Keep selection and final metadata distinct. August scores describe the selection-stage bundles; they are not generalisation scores for bundles subsequently fitted on August. Final bundles inherit the frozen algorithm choice and thresholds without reselection. Reports disclose that refitting can change probability behavior; threshold calibration on the final models is not claimed.

Alternative considered: fit once through July and ship that bundle. It is simpler but does not use August's eligible observations in the requested final training period. Selecting the winner on September would contaminate the demo comparison and is excluded.

### 2. Preserve the current bounded two-model search

Reuse seed 42, four CPU threads, a 2,000-row pilot, 20,000 tuning rows, four coarse and four refined candidates per model over two folds: 32 search fits. CatBoost uses verified GPU training with 50% GPU RAM; RF uses CPU. Keep the 600-second search and 2.5-GiB process RSS limits. Run fits sequentially and record time, memory and exact samples.

Account separately for two selection-stage fits, two final fits and one selected-configuration site-holdout refit, plus the small pilot/probes. The search time limit does not cover feature reading, final fits or explanations. Bind the measured proposal and the user's instruction to train both models as before to this run's configuration. If the pilot exposes an infeasible budget or unavailable GPU, report it before changing the agreed computation.

Alternative considered: reuse previous winning parameters without a search. This would omit the requested comparison under the revised training period.

### 3. Make the active input schema explicit

The 13 existing model inputs are `day_of_week`, `week_of_year`, `month`, `season`, `capacity_m3`, `resident_factor`, `waste_type`, `sub_district`, `object_group`, `holidays_since_last_collection`, `collections_last_28d`, `missed_collections_28d` and `qr_alerts`.

The eight added inputs are:

| Input | Definition for forecast date D |
|---|---|
| `days_since_last_successful_collection` | D minus the latest prior `collected`/`retry_collected` date |
| `days_since_last_collection_attempt` | D minus the latest prior date with status other than `none` |
| `previous_worker_rating` | Latest nonmissing assessment strictly before D |
| `days_since_previous_worker_rating` | D minus that assessment's date |
| `previous_collection_status` | Status on D-1, missing when that day's observation is unavailable |
| `collections_last_7d` | Successful collections in [D-7,D-1], missing for an incomplete window |
| `collections_last_90d` | Successful collections in [D-90,D-1], missing for an incomplete window |
| `missed_collections_last_90d` | Final missed collections in [D-90,D-1], missing for an incomplete window |

Only this schema is defined/computed by active ML code and described in current configuration and delivery documentation. Keep grouping identifiers and input-quality diagnostics separate from model inputs. Learned numerical medians, missingness handling and categorical treatment remain fitted on the applicable training sample. Preserve genuine zeros; support unseen categories; apply reviewed district aliases and existing invalid-capacity handling. The source `fill_level` remains an assessment/target, separate from the returned predicted `fill_level` in a new result frame.

### 4. Apply the explicit today/forecast-day availability contract

The DataFrame core accepts historical rows through T, a registry/reference snapshot and a separate D-keyed safe-counter frame. It generates D's calendar fields and historical inputs. Caller frames are copied as needed and never modified. A proposed interface is:

```python
predictor = FillPredictor.load(product_directory)
result = predictor.predict_next_day(
    history_df=history,
    registry_df=registry,
    today="2026-09-15",
    day_counters_df=safe_counters_for_2026_09_16,
    population_df=population,  # optional if exposure is already in the registry
)
# result columns: bin_id, fill_level
```

History can include all observations on T because selected "today" is interpreted as end-of-day, consistent with the existing data convention. D's current outcomes are ignored even if passed accidentally. The CSV demo adapter streams complete bins and projects the D row onto only bin/date keys and the four approved counters. D's other outcomes never enter the feature sequence. Dates after D cannot contribute. This is an explicit, user-confirmed safe-counter exception to the history-row cutoff, not permission to expose the D row generally.

Retain supplied D counters without another shift. When absent, reconstruct 28-day counts and holidays only from a complete, verified history window; a QR count is unknown unless a known prior success establishes reset zero. Do not synthesize reports. Future database callers must supply the same safe counter contract or accept the documented missingness. No database adapter is built now.

Alternative considered: shift D's safe counters again or carry forward T's counters. That changes the current feature meanings and contradicts the user's clarification.

### 5. Keep feature values ephemeral and memory bounded

Extract pure, IO-independent feature construction for reuse by training and product inference. Stream raw CSV in complete per-bin batches using the current bounded reader; calculate lag/window inputs before filtering labeled rows. Materialize only bounded training/tuning samples and the current evaluation/inference batch in memory, not the whole 23.8-million-row CSV.

Replace dependence on `features.parquet` and `registry_inputs/` feature snapshots with streamed batches and in-memory frames. Do not persist constructed feature vectors at training or inference stages. Persist only necessary source/sample keys, configuration, aggregate analysis tables, predictions explicitly produced by research commands, model parameters and bundles. Feature dictionaries and importance tables describe inputs without becoming caches of per-bin feature values.

The public predictor performs no file writes, including logging to a file, dumping input frames or exporting predictions. Research orchestration owns explicit result exports and report writing. Shared feature logic prevents divergent formulas between an eventual database caller and current CSV-based training.

Alternative considered: retain the existing Parquet cache dependency for runtime speed. It would make the handoff depend on persisted derived inputs and violate the requested memory-only behavior. Bounded in-memory construction trades extra raw reads for a simpler and verifiable contract.

### 6. Package one standalone winner and retain two research candidates

Use `backend/data/ml/september-fill-predictor/` as the only active run root. Its `models/` holds the two final candidates; selection-stage scores and provenance remain under analysis, without redundant obsolete model copies. A `product/` directory contains:

- `model.joblib`: a payload of standard-library/model-library objects, fitted preprocessing state and metadata, avoiding a pickle dependency on a custom `app.ml` class.
- A small importable `viptop_fill/` package with the loader, active feature builder, schema and normalization data. Training imports this same pure feature implementation; packaging copies the verified source and records checksums.
- Pinned CPU runtime requirements for the chosen algorithm and shared feature dependencies, a manifest with source/package hashes, versions, date semantics and ordered inputs, and an English developer README.
- A minimal DataFrame example and a CSV streaming demo adapter that obtains only permitted inputs. Neither requires database configuration, the original research run or the losing candidate.

Before delivery, copy the package to an isolated temporary directory, load it in a fresh process without the repository on its import path and compare its outputs to the selected final research model. Use CPU inference for CatBoost as well as RF. The provided registry determines the expected output IDs rather than hard-coding the current registry count; the full current demo still verifies all 21,951 unique bins.

The product returns exactly two columns and uses mapped five-class probability argmax. Keep P(3)+P(4), each frozen threshold and urgent flags available to the analysis layer. Report urgent F1 for both probability-sum decisions and grouped argmax so the two-column product is assessed honestly.

Alternative considered: export only the existing custom ModelBundle pickle. It requires the original Python module namespace and potentially cache-dependent imports, weakening standalone delivery.

### 7. Reproduce analysis using the product time semantics

Reuse existing EDA, multiclass/ordinal metrics, confusion matrices, error strata, native/permutation importance and bounded SHAP workflows with active features. Keep majority, stratified dummy and previous-assessment baselines plus useful training-derived comparisons; their learned state uses only the applicable pre-September period. Do not preserve an obsolete baseline merely to match a historical baseline count.

Compute both final models for all 30 demo "today" dates. Export research predictions, per-date and pooled scores, labeled denominators and paired comparison charts, including the 2026-09-15 -> 2026-09-16 example. Compare to D's synthetic labels only after features/predictions have been computed. Later demo days may use earlier September observations as history, but do not fit parameters or preprocessing from them.

Use the seeded 10% site holdout as a separate cold-start diagnostic: refit the selected configuration on pre-September labeled samples excluding held-out sites and evaluate their demo targets with the documented historical-input mask. It does not influence algorithm selection. Retain existing resource-bounded permutation/SHAP sample sizes (500/50) and disclose measured explanation limitations.

Every plotted result has a source table. Reports keep August selection-stage scores, final next-day comparisons and independent site diagnostics distinct. September dates were already observed in earlier experiments; describe the results as comparative, even though this run never selects on them.

### 8. Clean old experiments after verified replacement

The cleanup allowlist is exactly:

- `backend/data/ml/fill-classifier/`
- `backend/data/ml/fill-classifier-priority34-100k/`

First verify immutable input hashes, both final candidates, chart/table completeness, product isolation and all-registry next-day coverage. Then resolve each deletion target to an absolute path, require it to be an immediate allowed child of the intended ML root, reject links/junctions or unexpected targets, and use native PowerShell `Remove-Item -LiteralPath` for those targets. Do not enumerate paths and pass them to another shell for deletion. Record cleanup results in the new run.

Retain `.venv`, dependency caches, raw exports, source-generation scripts/docs and existing OpenSpec history. Current code and developer documentation must refer only to the current model/schema/run; historical OpenSpec records are not delivery documentation. Check the copied product again after deletion. No extra deletion confirmation is needed for these explicitly requested superseded runs.

## Risks / Trade-offs

- Synthetic, collection-day-selected labels -> disclose the labeled population and avoid real-world accuracy claims.
- Prior weak cold-start scores -> retain the separate diagnostic and explain the role of the previous assessment without equating coverage to confidence.
- Final refitting changes probabilities -> freeze selection/thresholds before refit, disclose their provenance and measure final demo behavior without retuning.
- Ephemeral features increase repeated CSV reading -> stream complete bins, retain bounded samples in memory and log actual resource usage.
- Target-day counters can accidentally expose outcomes -> explicitly project the four allowed columns and verify outcome perturbation invariance.
- Pickle/module portability -> export library-object payloads, ship the pure builder and verify a fresh process outside the repository.
- Two unarchived deltas share the ML capability -> keep this change's superseding decisions explicit and reconcile the old delta before any later archive; archive is not part of this implementation.

## Migration Plan

1. Implement the pure active builder, source adapter and next-day interface while keeping old artifacts available.
2. Configure the new periods and run bounded pilot/search, selection-stage fits, August selection and frozen final refits.
3. Generate the full comparative analysis and standalone product; run existing focused checks and explicit leakage/coverage/package checks.
4. Publish the verified current report and package, remove the two allowlisted old runs, then repeat isolated product prediction and source-hash verification.

Failures before verification leave prior experiment directories available. After cleanup, reproduce the current run from its immutable sources, pinned dependencies, saved configuration and sample keys; the deleted experiments are intentionally not retained as rollback copies. Application startup and database state require no migration.
