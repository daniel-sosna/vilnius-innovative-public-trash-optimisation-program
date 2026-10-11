# Spec Delta

## RENAMED Requirements

- FROM: `### Requirement: Bbox-only backend analysis request`
- TO: `### Requirement: Bbox and project-date backend analysis request`

## MODIFIED Requirements

### Requirement: Bbox and project-date backend analysis request
`POST /map-analytics/agent/analyze` SHALL accept a body containing only required `bbox` and September 2026 date-only `project_date`. It SHALL reject missing or invalid project dates and missing, nonfinite, out-of-range, reversed or zero-area bounds with HTTP 422 before provider use. Successful execution SHALL return the analyzed bbox, captured project date, default period, completion status and nullable analytical text.

#### Scenario: Send a confirmed selection
- **WHEN** the frontend submits a valid confirmed bbox and shared project date
- **THEN** the backend obtains analytical data through local read tools rather than receiving database records from the frontend

#### Scenario: Reject invalid input
- **WHEN** the body contains invalid bounds, extra analytical instructions or screen-pixel fields
- **THEN** the endpoint returns HTTP 422 without starting model execution

## ADDED Requirements

### Requirement: Calendar-bound adequacy investigation
The agent SHALL discover saved adequacy coverage in the initial area overview and investigate available September-to-date categories and reasons using read tools. Adequacy reads SHALL use the captured project date regardless of visible layers or waste filters. Existing non-adequacy observation windows SHALL retain their semantics, with differing evidence periods identified in findings.

#### Scenario: Risk layer is hidden
- **WHEN** an administrator analyzes a bbox with the risk layer disabled and September 18 selected
- **THEN** the agent can inspect all three waste streams for the saved September 1–18 assessment
- **AND** it explains candidate actions from tool evidence with the period and uncertainty in a separate `Konteinerių pakankamumas` section

#### Scenario: Missing saved assessment
- **WHEN** the exact selected cutoff is not imported
- **THEN** the agent identifies unavailable adequacy evidence and can continue other analysis
- **AND** it neither generates data nor substitutes a later assessment

### Requirement: Calendar changes invalidate agent results
Changing the shared project date SHALL cancel or discard pending analysis and clear its answer and error while preserving the confirmed bbox and map state. The administrator SHALL explicitly start a new analysis. A response for an earlier date SHALL NOT appear under the current date.

#### Scenario: Date changes during investigation
- **WHEN** an analysis for September 18 is pending and September 7 is selected
- **THEN** the pending run is cancelled or its response discarded and no stale answer appears
- **AND** the confirmed area remains available for an explicit new request

#### Scenario: Date changes after completion
- **WHEN** an answer for September 18 is visible and September 7 is selected
- **THEN** the answer is cleared without another model request or map recreation

### Requirement: Enforced answer presentation
Every returned analytical answer SHALL contain a nonempty separate Markdown
section headed `## Konteinerių pakankamumas`. It SHALL describe saved risk
evidence and its period, or distinguish unavailable, zero-match and failed
evidence. User-facing answers SHALL omit discussion of synthetic, artificial
or simulated data origin. Internal evidence provenance SHALL be preserved;
estimated/model evidence SHALL NOT be relabeled as recorded measurements.
The backend SHALL reject prohibited wording or a missing/empty section before
normal or SSE delivery. Corrections SHALL stay within the existing request and
time budgets; unresolved violations SHALL return no answer with an incomplete
`response_policy` reason.

#### Scenario: Model violates presentation rules
- **WHEN** the model produces prohibited provenance wording or omits the adequacy section
- **THEN** that text is not delivered to the administrator
- **AND** the backend requests a compliant rewrite within its remaining budget or returns an incomplete result without an answer
