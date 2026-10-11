# Spec Delta

## ADDED Requirements

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
