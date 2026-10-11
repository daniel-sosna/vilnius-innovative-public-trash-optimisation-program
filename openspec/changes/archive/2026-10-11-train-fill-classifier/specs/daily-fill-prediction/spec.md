# Spec Delta

## Purpose

Provide reproducible five-class daily fill predictions for the complete container registry, with temporal evaluation, explainable outputs and explicit synthetic-data limitations.

## ADDED Requirements

### Requirement: Validate authoritative inputs
The pipeline SHALL validate schemas, dates, unique daily keys, daily continuity, registry membership, target domains, missingness, categories and numerical validity. It SHALL report verified counts and a data dictionary, preserve raw files and exit nonzero on structural errors.

#### Scenario: Duplicate daily key
- **WHEN** two source rows have the same bin and date
- **THEN** validation fails with a useful error and publishes no successful feature cache

### Requirement: Enforce prediction-time availability
A prediction for date D SHALL use only observations before D and deterministic calendar information for D. Historical features SHALL be constructed on complete daily sequences before labeled-row selection. Existing QR and calendar counters that already exclude D SHALL not be shifted again.

#### Scenario: Current and future outcomes change
- **WHEN** labels or collection outcomes on D or later are changed
- **THEN** model features and predictions for D remain unchanged

### Requirement: Preserve missing observations and genuine zeros
The pipeline SHALL preserve source fill_level, treat NULL targets as unlabeled, retain genuine zero exposure and QR values, and fit learned preprocessing only on each training partition. Invalid capacity and unknown categories SHALL have explicit handling and input-quality flags.

#### Scenario: Missing QR differs from zero
- **WHEN** one bin has zero QR reports and another has unknown reports
- **THEN** the feature representation and quality flags distinguish them

### Requirement: Evaluate chronologically
Training, validation, temporal folds and test SHALL use non-overlapping date boundaries with training strictly earlier than evaluation. The first generator-calibration year SHALL serve as historical context. Test outcomes SHALL not select features, hyperparameters, calibration or decision rules.

#### Scenario: Retrospective control date
- **WHEN** predictions are requested for 2026-09-15
- **THEN** model fitting ends before that date and same-day synthetic labels are used only for retrospective comparison

### Requirement: Compare required models and baselines
Evaluation SHALL compare the five agreed dummy/historical baselines and CatBoost and Random Forest, using combined classes-3/4 F1 as the primary metric. It SHALL also report weighted F1, balanced accuracy, accuracy, per-class scores, confusion matrices, log loss, ordinal MAE, quadratic kappa, severe errors and classes-3/4 operational scores.

#### Scenario: Select the primary model
- **WHEN** validation comparison completes
- **THEN** selection uses validation combined classes-3/4 F1 with separately reported multiclass metrics and is frozen before final test evaluation

### Requirement: Bound and audit model search
The pipeline SHALL provide deterministic training-only tuning subsets, coarse/refined grids, common expanding temporal folds, weighting experiments, per-fit duration and fold scores. It SHALL report resource estimates and obtain user confirmation of the concrete budget before expensive search, then refit selected parameters on the user-authorized reduced documented training sample.

#### Scenario: Pilot exceeds the budget
- **WHEN** pilot time or memory makes the proposed grid infeasible
- **THEN** the pipeline reports a revised sample/grid and waits for confirmation rather than silently reducing the agreed search

### Requirement: Predict the complete registry
Inference SHALL return exactly one row per authoritative registry bin per requested date, including bins without history or valid generator inputs. Each row SHALL include bin_id, date, predicted_fill_level, five class probabilities and input_quality_flag. Flags SHALL distinguish missing QR/category, ambiguous district, invalid capacity, absent history/labels and multiple issues.

#### Scenario: Registry-only bin
- **WHEN** a registered bin has no daily-history rows
- **THEN** it receives a prediction from available static/calendar attributes and explicit missing historical features, without invented observations

### Requirement: Validate probability and model bundles
Saved and reloaded models SHALL produce finite five-class probabilities in [0,1], summing to one within tolerance, mapped by model.classes_. Predictions SHALL use probability argmax. Unknown categories SHALL be supported; folds missing a required class SHALL be handled explicitly rather than mislabeling columns.

#### Scenario: Reload and predict
- **WHEN** the selected model bundle is loaded in a fresh process
- **THEN** sample inference passes probability, class-domain, uniqueness and registry-coverage checks

### Requirement: Report quality and generalisation separately
Reports SHALL separate predictive performance, complete-registry coverage and input quality. They SHALL include an independent unseen-site evaluation, feature/distribution drift, native and held-out permutation importance, feasible SHAP explanations, class-4 examples and the tables behind charts.

#### Scenario: Complete coverage with missing history
- **WHEN** all registry bins receive predictions
- **THEN** the report identifies bins without labels/history and does not claim equal confidence or measured accuracy for them

### Requirement: Publish reproducible artifacts and limitations
Each run SHALL save configuration, input hashes, versions, logs, split/sample metadata, search results, fitted preprocessing/models, predictions, metrics, importance, charts and an English ML report. Documentation SHALL disclose synthetic labels, first-year generator calibration, collection-day selection, static snapshots, prolonged saturation and the need for real measurements.

#### Scenario: No real fill measurements
- **WHEN** observed service history contains only NULL fill_level
- **THEN** the control-date comparison is labeled synthetic and makes no claim of real-world predictive accuracy

User scope revision (2026-10-10): only CatBoost with hyperparameter search and smaller data, replacing the initial three-model run. Concrete conservative limits: 2,000-row pilot, 10,000 tuning rows, 50,000 final rows, two temporal folds, 16 search fits, 600 seconds of search, 2.5 GiB process RSS and 50% GPU RAM. The direct user instruction authorizes this reduced run; preserve it alongside the measured proposal. Marginal strata replace full joint strata because 49,679 full joint strata cannot fit a 10,000-row sample.

### Requirement: Prioritize combined urgent classes
The revised pipeline SHALL compare CatBoost and Random Forest by classes-3/4
binary F1 using summed class probability. It SHALL select each operational
threshold and the primary model using validation only, and report group
precision/recall/F1 alongside five-class argmax metrics and comparison charts.

#### Scenario: Two urgent classes split probability
- **WHEN** classes 3 and 4 individually lose argmax but their combined probability exceeds the frozen operational threshold
- **THEN** needs_collection is positive while predicted_fill_level retains five-class argmax

### Requirement: Apply the revised training inputs
Both models SHALL exclude historical_fill_mean, historical_fill_median and
historical_fill_std and their missingness indicators, retain the previous worker
rating and its age, tune on 20,000 rows and fit on 100,000 rows. The prior run
SHALL be preserved, and reused test dates SHALL be labeled comparative.

#### Scenario: Reload a model with exclusions
- **WHEN** a revised bundle is reloaded and excluded source columns are changed
- **THEN** its probabilities remain unchanged and the report identifies the retained historical rating inputs
