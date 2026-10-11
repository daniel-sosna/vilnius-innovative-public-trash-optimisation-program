# Spec Delta

## Purpose

Let administrators select a geographic map area and receive database-backed analysis through a bounded, read-only AI workflow without leaving the map.

## ADDED Requirements

### Requirement: AI area workflow in the shared sidebar
The shared map sidebar SHALL provide an AI mode containing `Pasirinkite plotą`, selected-area feedback, an analysis action and result feedback. Selection, pending analysis and results SHALL survive closing, reopening and switching sidebar modes within the page session.

#### Scenario: Return to an existing analysis
- **WHEN** an administrator closes or switches away from the AI panel and then reopens it
- **THEN** its confirmed area, pending state or result remains available without repeating selection or submitting another request

### Requirement: Rectangular selection on the existing map
Activating `Pasirinkite plotą` SHALL enter a visibly indicated mouse/touch rectangle-selection mode with a translucent draft rectangle. All enabled datasets and the camera SHALL be preserved. Competing map navigation and feature activation SHALL be suspended only during drawing/review and restored when selection ends.

#### Scenario: Draw over active datasets
- **WHEN** the administrator drags across the map with bins and polygon layers enabled
- **THEN** a visible rectangle follows the gesture while those layers remain visible
- **AND** the gesture does not pan the map, expand a cluster or open a feature popup

#### Scenario: Draw on a touch device
- **WHEN** a touch gesture creates an area selection
- **THEN** the rectangle can be drawn and reviewed without scrolling the page or moving the camera

### Requirement: Selection confirmation and retake
A valid draft SHALL expose `Patvirtinti`, `Pasirinkti iš naujo` and `Atšaukti`. Confirmation SHALL store a geographic bbox, exit selection mode and return to the AI workflow without starting analysis. Retake SHALL clear only the draft and permit another rectangle.

#### Scenario: Confirm a geographic area
- **WHEN** the administrator confirms a valid draft
- **THEN** the AI panel identifies that an area is selected and offers `Analizuoti pasirinktą plotą`
- **AND** the geographic area remains identifiable on the map after normal interaction resumes

#### Scenario: Retake a draft
- **WHEN** `Pasirinkti iš naujo` is activated during review
- **THEN** the draft is cleared and another rectangle can be drawn without changing layers or the camera

### Requirement: Selection cancellation preserves confirmed state
Cancelling selection SHALL discard the draft, restore prior interaction settings and return to the AI workflow without analysis. Any previously confirmed area and its result SHALL remain intact. A pointer cancellation SHALL not confirm an unfinished gesture.

#### Scenario: Cancel replacement of an area
- **WHEN** an administrator starts selecting another area and activates `Atšaukti` or presses Escape
- **THEN** the previous confirmed area and associated result remain available and no analysis starts

#### Scenario: Interrupt a gesture
- **WHEN** the device cancels an active pointer gesture
- **THEN** no unfinished rectangle is confirmed and the administrator can retry or exit selection

### Requirement: Geographic bbox contract
A selected area SHALL use finite `min_latitude`, `min_longitude`, `max_latitude` and `max_longitude` values in geographic ranges, with positive latitude and longitude spans. Drawing direction SHALL not affect normalization. Coordinates SHALL describe the actual bbox presented for confirmation rather than screen pixels.

#### Scenario: Draw in a reversed direction
- **WHEN** the administrator draws from bottom-right to top-left
- **THEN** minimum coordinates are below maximum coordinates and the same geographic area is selected as with the reverse gesture

#### Scenario: Select on a rotated or pitched map
- **WHEN** a screen rectangle is drawn on a rotated or pitched map
- **THEN** review shows the geographic bounding envelope of its corners and analysis uses that displayed envelope
- **AND** the camera is not reset to obtain the bbox

#### Scenario: Reject an empty or unusable draft
- **WHEN** a gesture has no geographic area or cannot produce valid coordinates
- **THEN** confirmation remains unavailable and the administrator can retake or cancel

### Requirement: Analysis scope is independent of visual filters
Analysis SHALL include eligible stored data inside the confirmed bbox regardless of layer visibility, loaded frontend datasets or waste-category filters. Broader comparisons SHALL be identified separately from selected-area results. Camera navigation SHALL not change a confirmed analysis scope.

#### Scenario: Analyze hidden bins
- **WHEN** bins are hidden or a waste category is unchecked and the administrator analyzes a confirmed area
- **THEN** matching database bins inside that area remain eligible for analysis
- **AND** the frontend sends neither active layers nor category filters as analytical restrictions

#### Scenario: Navigate during investigation
- **WHEN** the administrator pans away from the selected area while analysis runs
- **THEN** the analysis continues to use the original confirmed bbox

### Requirement: Bbox-only backend analysis request
`POST /map-analytics/agent/analyze` SHALL accept a body containing only the required `bbox` object. It SHALL reject missing, nonfinite, out-of-range, reversed or zero-area bounds with HTTP 422 before provider use. Successful execution SHALL return the analyzed bbox, default period, completion status and nullable analytical text.

#### Scenario: Send a confirmed selection
- **WHEN** the frontend submits a valid confirmed bbox
- **THEN** the backend obtains analytical data through local read tools rather than receiving database records from the frontend

#### Scenario: Reject invalid input
- **WHEN** the body contains invalid bounds, extra analytical instructions or screen-pixel fields
- **THEN** the endpoint returns HTTP 422 without starting model execution

### Requirement: Recent-first investigation with historical exploration
Analysis SHALL begin with the last 30 Europe/Vilnius calendar days including today, capped at the run's start time for timestamped observations. The agent SHALL be able to request explicit older periods or all available past observations when useful. Results SHALL identify effective periods and data coverage.

#### Scenario: Investigate sparse recent records
- **WHEN** the recent overview contains little data but older records exist
- **THEN** the agent can investigate older data and distinguish its findings from the default recent period

#### Scenario: Cross a daylight-saving boundary
- **WHEN** the 30-day period crosses a Europe/Vilnius clock change
- **THEN** the default still covers 30 local calendar dates rather than assuming a fixed UTC offset

### Requirement: Tool-led initial model context
The initial model request SHALL contain the bbox, replaceable generic analytical instructions, database/domain guidance and available tool descriptions, without prefetched database records. Factual analytical claims SHALL depend on returned tool evidence, and unavailable information SHALL be described as missing.

#### Scenario: Start an investigation
- **WHEN** the first model request is sent
- **THEN** no database row dump is included and the investigation starts by requesting the area overview

#### Scenario: Receive an empty area
- **WHEN** tools report no matching records
- **THEN** the response describes the lack of available evidence rather than inventing activity or treating missing data as zero-valued observations

### Requirement: Backend multi-step function execution
Analysis SHALL use the OpenAI Responses API with validated read-only function tools. It SHALL support multiple calls in a response and subsequent requests using their corresponding results. Unrecognized tools or invalid arguments SHALL not execute and SHALL produce controlled feedback.

#### Scenario: Investigate beyond the overview
- **WHEN** the model requests additional service and request summaries after reading the overview
- **THEN** the backend executes the validated tools and returns each result to its matching call before requesting another response

#### Scenario: Reject an unsupported tool
- **WHEN** a response requests an unknown tool or an out-of-contract argument
- **THEN** no arbitrary SQL, shell command or application mutation occurs

### Requirement: Five-request execution limit
Each analysis SHALL make at most five outbound model requests total. Requests one through four SHALL permit investigation; request five SHALL be reserved for synthesis with no callable tools. A complete final answer before request five SHALL finish the run early. Provider retries SHALL not create extra requests beyond this limit.

#### Scenario: Reach the synthesis request
- **WHEN** the fourth request returns tool calls and their results have been collected
- **THEN** the fifth request receives the accumulated evidence with tools disabled and no sixth request is made

#### Scenario: Finish early
- **WHEN** the second request produces a complete analytical answer without pending tool calls
- **THEN** that answer is returned without requesting unnecessary later responses

### Requirement: Sixty-second deadline and incomplete analysis
Each run SHALL have a 60-second backend execution deadline covering model requests, tool execution and any retries. No new work SHALL start after expiry. Deadline expiry or failure to obtain a complete final answer within the request limit SHALL return an explicit incomplete status and reason; missing final text SHALL not be fabricated.

#### Scenario: Exhaust the deadline
- **WHEN** provider waiting or tool execution reaches the 60-second deadline
- **THEN** outstanding work is cancelled or bounded by the remaining deadline and the response identifies incomplete analysis
- **AND** the AI panel retains the selection and offers retry

#### Scenario: Final response is truncated or empty
- **WHEN** the synthesis response cannot supply a complete analytical answer
- **THEN** the result is marked incomplete and any displayed partial text is clearly identified as partial

### Requirement: Pending analysis keeps the map usable
Pending analysis SHALL show live stage and data-check feedback based on actual execution, without exposing private model reasoning, and disable duplicate submissions and replacement of the confirmed area. Map navigation, layer controls, sidebar closing and mode switching SHALL remain usable. Completion or failure SHALL release the pending controls without changing the camera or layers.

#### Scenario: Switch panels while waiting
- **WHEN** the administrator switches to layers during analysis
- **THEN** layers remain controllable and reopening AI shows the same pending run
- **AND** selecting another area and submitting a duplicate analysis remain unavailable

### Requirement: Session results remain associated with their area
The AI panel SHALL display Markdown-formatted analytical text, including tables, with its area context and without a separate raw timestamp period line. Confirming another area SHALL clear the prior result from the current-area display. Responses arriving after navigation away from the page SHALL not restore stale UI state. No full chat or cross-session memory SHALL be required.

#### Scenario: Analyze another area
- **WHEN** a completed run is followed by confirmation of another bbox
- **THEN** the old answer is not presented as analysis of the new area
- **AND** the new area can be analyzed independently

### Requirement: Backend-only provider configuration
The backend SHALL use `OPENAI_API_KEY` and `OPENAI_MODEL` from its environment. Missing configuration SHALL produce a clear recoverable analysis error without preventing existing map endpoints from operating. Keys SHALL not appear in frontend configuration, responses, committed files or logs.

#### Scenario: Run without AI configuration
- **WHEN** analysis is requested without a usable key or model configuration
- **THEN** the endpoint returns HTTP 503 with a controlled configuration error and the map remains usable

### Requirement: Recoverable provider and tool failures
Provider authentication, connection, rate-limit and server failures SHALL produce controlled errors without secrets or raw exceptions. Tool failures SHALL be distinguishable from empty data. The UI SHALL retain the selected area, show Lithuanian error or incomplete feedback and allow an explicit retry without automatic resubmission.

#### Scenario: Provider rejects the request
- **WHEN** provider execution fails before a usable final response
- **THEN** the UI shows recoverable failure feedback, preserves selection and enables retry
- **AND** it displays no raw provider exception or secret

#### Scenario: A query fails
- **WHEN** a database tool fails while other evidence is available
- **THEN** the failed dataset is not described as an empty successful query and unsupported conclusions are withheld

### Requirement: Optional synthetic investigation remains distinct
Synthetic bin-day outcomes and stored mock predictions SHALL be available to the agent without being required in every run. Their results and analytical claims SHALL remain distinct from recorded service attempts, observed fill values and population estimates. Analysis SHALL not generate new predictions or plans.

#### Scenario: Use synthetic data for context
- **WHEN** the agent requests stored synthetic collection outcomes or mock predicted fill
- **THEN** the response identifies those sources as synthetic or mock prediction and does not use them as evidence of actual service quality

### Requirement: Bounded execution observability
Backend logging SHALL identify run start/completion, tool names, tool failures and provider failures with duration and request counts. Logs SHALL omit secrets, raw provider exceptions containing sensitive payloads and large tool-result bodies.

#### Scenario: Diagnose an incomplete run
- **WHEN** a run reaches its deadline
- **THEN** logs identify the run, elapsed time, model request count and incomplete reason without logging its key or database payloads

### Requirement: Completed analysis controls
A completed analysis SHALL hide `Analizuoti pasirinktą plotą`. Confirming a new area SHALL make the analysis action available again. Failed or incomplete analysis SHALL retain an explicit retry action.

#### Scenario: Review a completed answer
- **WHEN** analysis completes successfully
- **THEN** its formatted answer remains visible and the analyze action is hidden

#### Scenario: Follow live progress
- **WHEN** analysis starts an investigation round, executes a data tool or synthesizes its answer
- **THEN** the pending panel describes the actual stage or data category being checked
- **AND** no private reasoning text is displayed

### Requirement: Resident-request zero counts
Successful resident-request reads with zero submissions SHALL mean no resident requests for early emptying were recorded within the stated scope and period, including an empty table. Such results SHALL NOT be labelled unavailable or as failed reads. Failed reads SHALL remain distinct from zero counts.

#### Scenario: No resident requests
- **WHEN** a successful area overview reports zero resident submissions
- **THEN** analysis describes no recorded resident requests in that scope and period
- **AND** it does not invent a failed follow-up read

### Requirement: Animated progress without round numbers
Pending progress text SHALL pulse in opacity and change on each investigation round. It SHALL describe the current execution without displaying a round counter or private model reasoning. Reduced-motion preferences SHALL suppress the animation.

#### Scenario: Investigation advances
- **WHEN** the next investigation round starts
- **THEN** its progress phrase differs from the previous round and no round number is displayed
