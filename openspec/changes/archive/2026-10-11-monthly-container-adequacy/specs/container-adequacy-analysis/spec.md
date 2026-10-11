# Spec Delta

## Purpose

Identify residential areas with limited container capacity and explain how monthly level-4 fill assessments relate to that pressure using reproducible, saved geographic analysis.

## ADDED Requirements

### Requirement: Explicit analysis generation
Analysis SHALL run only on explicit invocation using the configured data directory or explicit input paths. It SHALL preserve source data and existing database allocations. Missing required registry exports, population geometry or fill inputs SHALL fail without publishing a result; generation SHALL NOT fetch development data from VASA.

#### Scenario: Generate from supplied exports
- **WHEN** an operator requests a month with valid source inputs
- **THEN** the command generates a saved analysis and reports its period, source coverage, exclusions and output path
- **AND** source files and database contents remain unchanged

#### Scenario: Required source missing
- **WHEN** a required input is missing or unreadable
- **THEN** generation identifies the input, exits unsuccessfully and preserves any published analysis

### Requirement: Residential capacity and access estimates
Analysis SHALL use the existing residential eligibility and nearest-point allocation separately for mixed, paper/plastic and glass waste. Capacity pressure SHALL be allocated residents divided by positive point capacity. Each population area SHALL reference its serving point, pressure and centroid-to-point ground distance, even when that point lies outside the area.

#### Scenario: Different capacity at one point
- **WHEN** a point serves 600 estimated residents and has containers of capacity 1 and 2 m³ for one waste type
- **THEN** its pressure is 200 estimated residents per m³
- **AND** every population area assigned to that point references that same point pressure

#### Scenario: Point outside the population polygon
- **WHEN** the nearest eligible point lies outside the area's boundary
- **THEN** it remains the serving point and its distance is retained
- **AND** an empty count of bins physically inside the area does not imply absent service

### Requirement: Conserved geographic capacity attribution
Each area SHALL retain its estimated residents and an attributed share of its serving point's capacity proportional to those residents. Attribution SHALL be identified as an estimate, not physical capacity inside the polygon. For each waste type, known residents SHALL be conserved across areas and each point's attributed capacity SHALL sum to its capacity when it serves residents.

#### Scenario: Shared serving point
- **WHEN** areas with 100 and 200 estimated residents share a point with capacity 3 m³ and no other assigned residents
- **THEN** attributed capacity is 1 and 2 m³ respectively
- **AND** neither area claims to physically contain the point's full capacity

### Requirement: Population and service gaps remain explicit
Unknown population SHALL remain unknown, and suppressed population SHALL retain its assumption. Areas with no eligible point SHALL have unknown pressure, zero attributed service capacity and an explicit service-gap reason. Areas with no resident demand SHALL not receive invented pressure or a shortage classification.

#### Scenario: Missing population density
- **WHEN** an area has no known or suppressed population density
- **THEN** its assessment is unavailable rather than classified as zero population or adequate service

#### Scenario: No eligible glass point
- **WHEN** a populated area has no eligible glass point in the input registry
- **THEN** the glass result identifies unavailable residential service without dividing by zero

### Requirement: Monthly level-four assessment statistics
Level-4 frequency SHALL be the number of known fill assessments equal to 4 divided by all known assessments in the period for the serving point and waste type. Counts SHALL use unique bin/day observations. Missing labels SHALL not enter the denominator. Invalid labels, duplicate bin/day keys and inconsistent registry references SHALL fail before publication.

#### Scenario: Missing assessments
- **WHEN** the serving point has 20 known assessments, 5 at level 4, and 40 unlabeled bin-days
- **THEN** the raw frequency is 25%, with counts 5 and 20
- **AND** unlabeled days are not treated as non-overflows

#### Scenario: Shared point evidence
- **WHEN** multiple areas reference the same serving point
- **THEN** their fill evidence identifies that point and is described as shared evidence
- **AND** a summary does not add those repeated point counts as independent events

### Requirement: Uncertainty and coverage accompany assessment estimates
Analysis SHALL expose raw counts, assessed days, assessed-bin coverage, a smoothed level-4 estimate and an uncertainty interval. A documented reproducible method SHALL separate sufficient evidence from sparse or absent evidence. No-assessment results SHALL have unknown fill frequency rather than a fabricated zero or a prior-only observed result.

#### Scenario: Single assessment
- **WHEN** a point has one known assessment at level 4
- **THEN** its raw count remains visible but the result identifies insufficient evidence for a confident monthly conclusion

### Requirement: Explainable adequacy categories
Analysis SHALL distinguish priority shortage, potential shortage, level-4 assessments without elevated capacity pressure, ordinary pressure without elevated level-4 evidence, insufficient fill evidence and unavailable assessment. Capacity/access thresholds SHALL remain fixed for the same reference snapshot across months. Categories SHALL retain their component values, applied thresholds and reason codes.

#### Scenario: High pressure with elevated level-four evidence
- **WHEN** pressure exceeds its waste-specific reference threshold and sufficient fill evidence exceeds the recorded level-4 criterion
- **THEN** the area is a priority shortage candidate with both reasons
- **AND** the result recommends checking capacity or collection frequency without asserting a proven cause

#### Scenario: High pressure without fill evidence
- **WHEN** capacity pressure is elevated but no fill assessments are available
- **THEN** the result retains the pressure flag and identifies insufficient fill evidence
- **AND** missing labels do not turn the area into an ordinary or confirmed-shortage result

### Requirement: Complete-month coverage
Initial generation SHALL publish complete-calendar-month results only when the source bin-day calendar covers that entire month for the declared eligible cohort. Sparse fill labels SHALL be reported separately from calendar coverage. Incomplete boundary months SHALL not be presented as completed months or silently filled using synthetic extensions.

#### Scenario: Retained source interval
- **WHEN** the source calendar spans June 1 through October 9, 2026 with complete daily coverage for its declared cohort
- **THEN** June, July, August and September are eligible complete months
- **AND** October is not published as a complete month

### Requirement: Self-contained monthly GeoJSON artifacts
Each generated month SHALL produce one GeoJSON FeatureCollection containing all three waste types with stable area/type identities and preserved population polygon geometry. The file SHALL contain period bounds, completion status, method/schema versions, source fingerprints, thresholds, provenance and quality information sufficient to interpret its feature metrics without reading the source CSV.

#### Scenario: Transfer a result
- **WHEN** a valid monthly file is copied into another configured analysis output directory
- **THEN** its period, geometry, metrics, provenance and legend categories remain interpretable without the original source data

### Requirement: Preserve published completed analyses
Published completed-month files SHALL be reused without modification during map access and repeated generation with the same inputs and parameters. Replacing a completed result SHALL require explicit regeneration. New and replacement files SHALL become visible only after complete validation; an unsuccessful generation SHALL preserve the last valid result.

#### Scenario: Generate an existing month
- **WHEN** a completed month exists with the same input fingerprints and parameters
- **THEN** generation reports reuse and leaves the saved bytes unchanged

#### Scenario: Source changes
- **WHEN** source fingerprints change for an existing completed month without explicit regeneration
- **THEN** generation reports the mismatch and preserves the published result

### Requirement: Honest result interpretation
Artifact metadata SHALL distinguish observed, synthetic, estimated and assumed inputs. They SHALL disclose static registry/population snapshots, collection-day assessment selection and dependence of synthetic fill on resident pressure. Results SHALL not claim measured overflow duration, causal container shortage, verified live presence or predictive accuracy.

#### Scenario: Synthetic level-four association
- **WHEN** the supplied enriched CSV provides synthetic fill assessments
- **THEN** the saved file retains synthetic provenance and assumptions, while compact map conclusions remain candidate actions without claiming observed causal shortages

### Requirement: Deferred shared-today integration
Until a shared selected-today capability exists, this feature SHALL provide completed-month analysis without a separate date selector or automatic date-change behavior. When that capability is implemented, its integration MUST also generate, publish and import month-to-date GeoJSON through this analysis pipeline and refresh the map catalog and selected result.

#### Scenario: Shared date not implemented
- **WHEN** the initial monthly feature is delivered without a shared selected-today capability
- **THEN** completed-month analysis remains usable and the dependency is recorded as deferred
- **AND** the UI does not claim to recalculate on date changes

#### Scenario: Shared date becomes available
- **WHEN** the project implements selected-today and selects September 18, 2026
- **THEN** its integration generates an analysis covering September 1 through 18 inclusive, marked incomplete, and makes it selectable on this map
- **AND** records after September 18 cannot affect its counts, statistical fitting or category thresholds

#### Scenario: Advance or reverse the shared date
- **WHEN** selected-today changes within or between months
- **THEN** the integration publishes the matching period without rewriting completed months, hides results later than the selected date and prevents a late old-date result from replacing the current selection

### Requirement: Explicit database publication
An explicit import command SHALL validate complete monthly GeoJSON files before writing them to the analysis table. Each row SHALL preserve the collection type, all feature geometry/properties and analysis metadata, identified by its stable analysis ID and source-file content revision. Import SHALL atomically upsert selected months only, preserve unrelated months and leave the database unchanged on any invalid input or transaction failure.

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
