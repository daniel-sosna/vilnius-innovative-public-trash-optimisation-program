# Spec Delta

## ADDED Requirements

### Requirement: Adequacy evidence discovery
The initial area overview SHALL report whether the exact September cutoff is imported, its identity, revision, bounds, completion and provenance, and whether valid adequacy polygons intersect the bbox. Missing saved results SHALL be distinct from zero matching features and failed reads. Discovery SHALL NOT generate data or return an unbounded feature collection.

#### Scenario: No saved cutoff
- **WHEN** the overview runs for September 18 but only September 30 exists
- **THEN** the exact cutoff is reported unavailable without using September 30
- **AND** other available analytical datasets remain discoverable

#### Scenario: Saved cutoff has no spatial matches
- **WHEN** a valid saved cutoff exists but no valid feature intersects the bbox
- **THEN** the overview reports available analysis with zero geographic matches

### Requirement: Adequacy geographic summaries
A read-only tool SHALL summarize saved cutoff features intersecting the bbox by waste type and category, with counts, known/missing population and unique serving-point evidence. Actual polygon intersection SHALL respect holes and include boundaries. Full-polygon estimates SHALL be labeled as intersecting-polygon totals, not residents inside the bbox; waste-stream populations SHALL NOT be summed as unique residents.

#### Scenario: Polygon envelope overlaps a hole
- **WHEN** the bbox lies entirely within a polygon hole
- **THEN** that feature is excluded from the summary

#### Scenario: Serving point outside selection
- **WHEN** an intersecting area is assigned a serving point outside the bbox
- **THEN** its saved risk and serving-point evidence remain included as external service context

#### Scenario: Multiple areas share evidence
- **WHEN** three intersecting mixed-waste areas share a point with five level-4 assessments out of twenty
- **THEN** the summary counts three areas and one serving point with counts five and twenty
- **AND** evidence is not inflated to fifteen out of sixty

### Requirement: Bounded adequacy feature investigation
Read-only tools SHALL list and inspect matching saved features with waste type, category, reasons, pressure/reference, distance, population, capacity attribution, assessment counts, coverage, smoothed frequency and uncertainty. Listings SHALL use deterministic pagination with default 50 and maximum 100; detail IDs SHALL be constrained to intersecting features of the captured artifact. Geometry SHALL NOT be returned in raw listings.

#### Scenario: Inspect a priority candidate
- **WHEN** the agent requests an intersecting priority feature
- **THEN** it receives saved component values and thresholds with artifact identity, revision and period
- **AND** unknown metrics remain null

#### Scenario: Invalid detail scope or pagination
- **WHEN** the agent requests an out-of-area feature, unsupported filter or limit above 100
- **THEN** it receives controlled validation feedback without an unbounded read

### Requirement: Adequacy provenance and consistent artifact reads
Internal adequacy tool evidence SHALL identify synthetic or observed fill provenance, static estimated population/capacity, sufficiency criteria and category meanings. A run SHALL pin its artifact identity and revision; replacement SHALL yield controlled stale-evidence feedback rather than mix revisions. Tools SHALL NOT read source CSVs, fit statistics or import data, and SHALL NOT describe categories as proven shortage or predicted overflow.

#### Scenario: Synthetic shortage association
- **WHEN** synthetic level-4 evidence and high static pressure support a priority category
- **THEN** results retain the synthetic assumptions and recommend checking capacity or frequency without claiming observed causality

#### Scenario: Artifact replaced during investigation
- **WHEN** an explicitly imported replacement changes the revision after discovery
- **THEN** later risk reads return stale-evidence feedback without mixing the replacement into the run
