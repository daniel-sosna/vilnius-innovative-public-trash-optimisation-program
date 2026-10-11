# daily-fill-prediction Specification

## Purpose

Provide reproducible next-day fill predictions for every registered container using historical data and one selected model, with pre-September training, comparative synthetic evaluation and a portable developer package.

## Requirements

### Requirement: Preserve the historical source
The pipeline SHALL treat the supplied enriched daily CSV and its authoritative reference inputs as immutable. Current training and demonstration SHALL work without database access or data regeneration. Source hashes SHALL identify the inputs used by the delivered model.

#### Scenario: Complete a run
- **WHEN** training, evaluation and product verification finish
- **THEN** the source files have their original hashes and no database ingestion or modification has occurred

### Requirement: Interpret the demo date as today
For a selected date T from 2026-09-01 through 2026-09-30, the product SHALL predict D=T+1 using historical observations through T inclusive. Deterministic calendar attributes SHALL describe D. Dates SHALL use the existing Europe/Vilnius data-day convention.

#### Scenario: Mid-month selection
- **WHEN** today is selected as 2026-09-15
- **THEN** the forecast is for 2026-09-16 and observations dated 2026-09-15 can contribute to its historical features

#### Scenario: End-of-month selection
- **WHEN** today is selected as 2026-09-30
- **THEN** the forecast is for 2026-10-01

### Requirement: Accept safe forecast-day source counters
Inference SHALL retain `holidays_since_last_collection`, `collections_last_28d`, `missed_collections_28d` and `qr_alerts` from the D row when supplied. Their defined windows exclude D, so they SHALL NOT be shifted again. This explicit exception SHALL NOT permit reading D's fill assessment or collection outcome.

#### Scenario: Preserve a supplied counter
- **WHEN** the D row supplies a valid QR counter and a fill assessment
- **THEN** the QR value enters the model unchanged and the assessment is ignored

### Requirement: Prevent future-outcome leakage
Feature construction SHALL use only outcomes before D, plus D's calendar/static attributes and approved safe counters. Learned preprocessing, parameter selection, model selection and threshold selection SHALL use no dates on or after 2026-09-01.

#### Scenario: Tomorrow's outcomes change
- **WHEN** D's fill assessment, D's collection outcome or any later outcome changes while permitted inputs remain fixed
- **THEN** the features and prediction for D remain unchanged

### Requirement: Construct historical inputs in memory
The supplied feature script SHALL calculate the eight active added historical inputs from complete per-bin daily history, preserving unlabeled days. It SHALL support caller-provided DataFrames and produce the same input semantics for training and inference. Constructed feature DataFrames SHALL remain in memory and SHALL NOT be persisted.

#### Scenario: Predict after loading history
- **WHEN** a caller provides historical and reference DataFrames
- **THEN** the script constructs model inputs in memory, leaves the caller's frames unchanged and creates no feature files

### Requirement: Define missing history explicitly
Missing observations SHALL remain distinguishable from genuine zero values. Unknown categories and invalid capacity SHALL receive the existing explicit handling. Missing history SHALL NOT be replaced by simulated outcomes. Missing forecast-day counters SHALL use documented missingness handling or a demonstrably complete historical reconstruction.

#### Scenario: Unknown QR count
- **WHEN** no safe QR count is supplied and historical data cannot establish it
- **THEN** the QR feature is missing rather than an invented zero

### Requirement: Validate inputs and cover the registry
The pipeline SHALL validate required columns, dates, unique bin/day keys, category/target domains and registry membership. Inference SHALL return exactly one prediction for every unique authoritative registry bin, including bins without historical assessments. Structural errors SHALL produce an actionable failure without partial product output.

#### Scenario: Registry-only bin
- **WHEN** a registered bin has no historical daily rows
- **THEN** it receives a prediction using available static/calendar attributes and explicit missing historical inputs

#### Scenario: Duplicate history
- **WHEN** two historical rows have the same bin and date
- **THEN** inference fails with a duplicate-key explanation

### Requirement: Retain the active model input contract
Both candidate models and the developer package SHALL use the same 21 active original-variable inputs, including the previous assessment and its age. Identifiers SHALL be keys rather than learned numeric inputs. Current feature definitions, configuration and delivery documentation SHALL describe only this active schema.

#### Scenario: Reload the product
- **WHEN** the selected bundle is loaded in a fresh process
- **THEN** its feature order and preprocessing agree with the delivered active feature dictionary

### Requirement: Select models before September
The pipeline SHALL compare CatBoost and Random Forest using chronological folds before the August selection period. Each selection-stage model SHALL fit on dates before August; August labels SHALL select the algorithm and operational threshold. Selection SHALL be frozen before final refits or demo evaluation.

#### Scenario: Freeze the winner
- **WHEN** August comparison finishes
- **THEN** a selection record identifies the chosen algorithm, parameters and threshold, using no September or October labels

### Requirement: Refit both candidates before the cutoff
Each frozen candidate SHALL receive a deterministic 100,000-row final training sample drawn from eligible labeled dates through 2026-08-31 inclusive. The first generator-calibration year SHALL serve as historical context rather than supervised fitting. No final fitting or learned preprocessing SHALL use September or October rows.

#### Scenario: Check final provenance
- **WHEN** either final bundle is inspected
- **THEN** its sample keys and metadata show a training period ending 2026-08-31 and no fitted row dated 2026-09-01 or later

### Requirement: Bound and reproduce parameter search
Search SHALL retain 20,000-row tuning samples, two temporal folds and four coarse plus four refined candidates per algorithm. The run SHALL record sample keys, seeds, parameters, per-fit durations and resources. The existing ten-minute search and 2.5-GiB process limits SHALL apply; infeasible limits SHALL fail explicitly rather than silently change scope.

#### Scenario: Audit search execution
- **WHEN** the search finishes
- **THEN** its record accounts for 32 candidate/fold fits and identifies the sample and date boundaries of every fit

### Requirement: Prioritize and disclose urgent-class decisions
Primary model selection SHALL use combined classes-3/4 F1 from P(3)+P(4), with each threshold selected only on August validation. Reports SHALL also disclose urgent precision, recall and F1 obtained by grouping the product's five-class argmax output, so operational scores are not mistaken for product-output scores.

#### Scenario: Probability sum and argmax disagree
- **WHEN** the frozen urgent threshold is exceeded but the five-class argmax is class 2
- **THEN** the research urgent flag is positive, the product returns class 2 and both scoring rules remain distinguishable in the report

### Requirement: Return the minimal product result
The product SHALL return a DataFrame with exactly `bin_id` and `fill_level`, where `fill_level` is the integer 0..4 probability-argmax prediction. Predicted values SHALL remain separate from historical assessments. Runtime invocation SHALL perform no implicit file writes and SHALL require no training cache or research output directory.

#### Scenario: Product response
- **WHEN** prediction succeeds for the authoritative registry
- **THEN** the result has exactly two columns, unique bin identifiers, no missing predicted levels and one row per registry bin

### Requirement: Validate probability interpretation
Both candidate bundles SHALL map probabilities through their saved class labels and produce five finite probabilities in [0,1] summing to one within tolerance. Saved preprocessing SHALL be reused without fitting during inference, with support for missing and unseen categories.

#### Scenario: Fresh-process prediction
- **WHEN** a bundle is reloaded and receives missing values or an unseen category
- **THEN** it produces valid probabilities and the product's predicted class follows their mapped argmax

### Requirement: Compare complete demo scenarios
After selection is frozen, both final models SHALL be evaluated for all 30 selected September dates and their next-day targets, 2026-09-02 through 2026-10-01. Assessments SHALL be joined only after prediction. Reports SHALL identify the labeled denominator and describe results as comparisons with synthetic labels on previously inspected dates.

#### Scenario: Unlabeled target day
- **WHEN** a registry bin has no synthetic assessment on a forecast date
- **THEN** it still receives a prediction but contributes no invented target to accuracy metrics

### Requirement: Retain comparative analytical coverage
The current run SHALL include EDA, baselines using the active inputs, per-class and urgent metrics, raw/normalized confusion matrices, ordinal errors, per-date/waste/capacity/quality errors, training resources, native/permutation importance, bounded feasible SHAP and a separate unseen-site cold-start diagnostic. Each chart SHALL have an underlying table.

#### Scenario: Review comparison charts
- **WHEN** developers inspect the final report
- **THEN** they can compare both models, trace charts to tables and distinguish model-selection results from final-model demo results and cold-start diagnostics

### Requirement: Deliver an independently usable predictor
The product package SHALL contain the selected final model with fitted preprocessing, active feature script/schema, static normalization data, version/dependency metadata, developer instructions and a minimal CPU inference example using caller-provided frames. It SHALL not require the other candidate bundle, database configuration or research caches.

#### Scenario: Developer handoff
- **WHEN** a developer uses only the product package, its declared dependencies and supplied input DataFrames
- **THEN** they can reproduce verified next-day predictions without the original experiment folders

### Requirement: Retain only current experiment artifacts
After the new models, comparisons and standalone package pass verification, cleanup SHALL remove only the two explicitly superseded experiment directories. It SHALL preserve the current run, immutable sources, shared runtime and unrelated project work. The current package and report SHALL have no runtime dependency on deleted artifacts.

#### Scenario: Successful cleanup
- **WHEN** delivery verification succeeds
- **THEN** the two superseded run directories are absent and the new package can still predict in a fresh process

#### Scenario: Failed replacement
- **WHEN** new training or package verification fails
- **THEN** cleanup has not removed the previous experiment directories

### Requirement: Report limitations and provenance
An English report SHALL record actual source hashes, date partitions, sample coverage, search/refit parameters, selection, thresholds, model metrics, artifacts and runtime. It SHALL disclose synthetic assessments, collection-day label selection, static snapshots, missing-history performance and repeated evaluation of previously inspected dates.

#### Scenario: Report complete coverage
- **WHEN** all authoritative registry bins receive predictions
- **THEN** the report distinguishes coverage from measured labeled-subset accuracy and does not claim verified real-world accuracy

### Requirement: Real prediction application endpoint
`POST /demo/predictions` SHALL accept `project_date` as a September 2026 `YYYY-MM-DD` day T and invoke the delivered real predictor against its configured immutable CSV inputs. It SHALL forecast T+1 without changing the standalone two-column output contract, retraining, rebuilding collection plans or writing source data.

#### Scenario: Request next-day predictions
- **WHEN** the application posts `{"project_date":"2026-09-14"}`
- **THEN** the predictor receives today `2026-09-14` and the successful API response identifies forecast date `2026-09-15`
- **AND** selection is derived from the real predictor's argmax fill output

#### Scenario: Reject an invalid input day
- **WHEN** the request contains an impossible date, timestamp or date outside September 2026
- **THEN** the API returns `422` before invoking inference

### Requirement: Application service-bin selection
The prediction response SHALL include input/forecast dates, evaluated-bin and due-bin counts, and due bins selected by argmax fill level greater than 2. Each due bin SHALL retain its model level and stored identity with coordinates where valid. Missing coordinates SHALL be disclosed separately from zero due bins.

#### Scenario: Apply the service threshold
- **WHEN** the real product returns levels 0, 1, 2, 3 and 4
- **THEN** levels 3 and 4 are selected, and the evaluated count covers the authoritative registry
- **AND** the selection does not substitute the research probability-sum urgent flag for argmax

#### Scenario: A selected bin lacks coordinates
- **WHEN** a due registry bin exists in the database but lacks valid coordinates
- **THEN** its identity and prediction remain in the result with unusable coordinates identified
- **AND** it contributes to the due count and missing-coordinate count

### Requirement: Explicit inference prerequisites and failures
Missing model artifacts, input files or runtime configuration SHALL produce an actionable non-success response without mock predictions. Invalid inference data or registry/database identity mismatch SHALL fail without partial selected output. Unexpected failures SHALL not expose credentials or internal traces to the frontend.

#### Scenario: Product package absent
- **WHEN** the configured trained model or its normalization artifact is unavailable
- **THEN** the API reports unavailable inference prerequisites and returns no substituted fill levels

#### Scenario: Registry does not align with stored bins
- **WHEN** an authoritative registry bin cannot be matched unambiguously to a stored bin
- **THEN** inference integration fails explicitly instead of silently dropping it or assigning another bin's location

### Requirement: Support the accepted inference duration
The application request path SHALL accommodate the existing approximately 4–5 minute real inference duration without a shorter default timeout or substituted cached predictions. Inference SHALL not block unrelated API handling. The caller SHALL have a finite timeout and actionable timeout feedback.

#### Scenario: Successful long request
- **WHEN** configured inference completes after five minutes
- **THEN** its response reaches the caller through the development proxy and the real result is processed
- **AND** unrelated API requests can be served while inference runs

#### Scenario: Inference does not finish in time
- **WHEN** the caller's configured finite timeout expires
- **THEN** it receives timeout feedback and can release the demo lock without displaying a successful prediction
