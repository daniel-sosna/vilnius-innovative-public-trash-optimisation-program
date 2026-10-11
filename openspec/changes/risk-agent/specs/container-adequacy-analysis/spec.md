# Spec Delta

## MODIFIED Requirements

### Requirement: Complete-month coverage
Generation SHALL publish complete-calendar-month results only when the source bin-day calendar covers that entire month for the declared eligible cohort. Sparse fill labels SHALL be reported separately from calendar coverage. Incomplete boundary months SHALL not be presented as completed months or silently filled using synthetic extensions.

#### Scenario: Retained source interval
- **WHEN** the source calendar spans June 1 through October 9, 2026 with complete daily coverage for its declared cohort
- **THEN** June, July, August and September are eligible complete months
- **AND** October is not published as a complete month

#### Scenario: Complete calendar for a partial period
- **WHEN** September 1–18 has every required cohort bin/day but September 19–30 is outside the requested period
- **THEN** the result reports complete source coverage for the requested period and `complete: false` for month completion
- **AND** a missing required day within September 1–18 prevents publication


### Requirement: Self-contained monthly GeoJSON artifacts
Each generated month or dated month-to-date period SHALL produce one GeoJSON FeatureCollection containing all three waste types with stable area/type identities and preserved population polygon geometry. Dated results SHALL have distinct stable identities without replacing completed-month identities. The file SHALL contain period bounds, completion status, method/schema versions, source fingerprints, thresholds, provenance and quality information sufficient to interpret its feature metrics without reading the source CSV.

#### Scenario: Transfer a result
- **WHEN** a valid monthly file is copied into another configured analysis output directory
- **THEN** its period, geometry, metrics, provenance and legend categories remain interpretable without the original source data

#### Scenario: Preserve completed-month identity
- **WHEN** dated September 18 and September 30 artifacts are published beside an existing completed September artifact
- **THEN** all identities remain distinct and the existing completed-month file is unchanged
- **AND** dated September 30 reports `complete: true`, while earlier cutoffs report `complete: false`


### Requirement: Deferred shared-today integration
The shared September date SHALL select an explicitly prepared and imported month-to-date result. Preparation SHALL produce all 30 September 2026 cutoffs in advance. Calendar changes SHALL only read the matching saved result, hide later results and preserve completed months; map and agent reads SHALL NOT generate or import data.

#### Scenario: Shared date not implemented
- **WHEN** a caller uses completed-month discovery without supplying a shared selected date
- **THEN** completed-month analysis remains available without automatic date-change behavior
- **AND** no partial September cutoff is inferred or generated

#### Scenario: Shared date becomes available
- **WHEN** the project implements selected-today and selects September 18, 2026
- **THEN** the map selects the prepared analysis covering September 1 through 18 inclusive, marked incomplete
- **AND** records after September 18 cannot affect its counts, statistical fitting or category thresholds

#### Scenario: Advance or reverse the shared date
- **WHEN** selected-today advances or reverses within September
- **THEN** the integration selects the matching saved period without rewriting completed months, hides results later than the selected date and prevents a late old-date result from replacing the current selection

### Requirement: Explicit database publication
An explicit import command SHALL validate completed-month and dated month-to-date GeoJSON files before writing them to the analysis table. Each row SHALL preserve the collection type, all feature geometry/properties and analysis metadata, identified by its stable analysis ID and source-file content revision. Import SHALL atomically upsert selected artifact identities only, preserve unrelated months and leave the database unchanged on any invalid input or transaction failure.

#### Scenario: Import generated months
- **WHEN** valid monthly files are explicitly imported
- **THEN** their collections become available to the database-backed map without source CSV access
- **AND** importing the same content again preserves the same ID and revision without duplicate rows

#### Scenario: Invalid batch or replacement
- **WHEN** one selected file is invalid or a batch write fails
- **THEN** previously imported months and revisions remain unchanged

#### Scenario: Replace one month
- **WHEN** an operator explicitly imports a regenerated file for an existing ID
- **THEN** that ID receives the complete replacement and its new revision
- **AND** other months remain unchanged

#### Scenario: Import prepared cutoffs
- **WHEN** the 30 valid September cutoff files are imported together
- **THEN** every dated result is stored with its exact bounds, completion flag and revision
- **AND** one invalid cutoff causes the entire selected import batch to leave the database unchanged


## ADDED Requirements

### Requirement: Cutoff-safe assessment fitting
A dated September result SHALL use only September 1 through its cutoff inclusive for counts, coverage and learned assessment statistics. Later observations SHALL NOT influence smoothed estimates, uncertainty or classification. Pressure/access references SHALL remain fixed from the declared static snapshot; fingerprints SHALL identify the immutable inputs and cutoff.

#### Scenario: Change later assessments
- **WHEN** assessments after September 18 change while the September 1–18 inputs, static snapshot and policy remain identical
- **THEN** the September 18 numerical metrics, fitted priors and categories remain identical
- **AND** source fingerprints can identify a changed input file without claiming changed cutoff evidence

#### Scenario: Sparse first day
- **WHEN** September 1 contains few or no known fill labels but has valid cohort calendar coverage
- **THEN** preparation preserves missing frequencies and reports insufficient evidence without fabricating labels

### Requirement: Repeatable advance preparation
An explicit preparation invocation SHALL generate all September cutoffs using declared immutable sources and parameters, report each period and publication outcome, and reuse identical saved results. Changed inputs or parameters SHALL require explicit regeneration. Failure SHALL preserve previously valid artifacts and report unsuccessful preparation.

#### Scenario: Prepare twice
- **WHEN** an operator repeats preparation with identical inputs and parameters
- **THEN** all 30 cutoff identities are reported as reused with unchanged bytes
- **AND** no completed-month artifact is rewritten
