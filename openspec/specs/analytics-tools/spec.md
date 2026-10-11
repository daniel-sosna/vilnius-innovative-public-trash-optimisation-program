# analytics-tools Specification

## Purpose

Provide composable read-only analytical queries over stored VipTop data so an area analyst can discover evidence, compare periods and explain results with clear scope and provenance.

## Requirements

### Requirement: Analytical queries cannot mutate application data
Agent tools SHALL read stored data only. They SHALL not expose arbitrary SQL, shell execution, imports, resident-request submission, entity mutations, plan generation or model execution. Failed or rejected calls SHALL not publish database changes.

#### Scenario: Request a write or arbitrary query
- **WHEN** a caller requests an unsupported mutation or arbitrary SQL operation
- **THEN** no such tool is available and no application data changes

### Requirement: Typed discoverable analytical contracts
Each exposed tool SHALL have a stable name, a typed strict parameter contract and a structured result. Its catalogue SHALL explain purpose, usage, parameters, units, dates, scope, output, NULL behavior and limitations. Unsupported tool names, grouping dimensions and intervals SHALL be rejected predictably.

#### Scenario: Choose a supported query
- **WHEN** the agent inspects available tool descriptions
- **THEN** it can distinguish a summary from a raw listing and determine its scope, evidence type and parameter meanings

### Requirement: Spatial point discovery
Area queries SHALL include points on the bbox boundary and use each bin's own coordinates. Site-location queries SHALL use stored site coordinates and distinguish those sites from sites represented by selected bins. Undisplayable coordinates SHALL not become valid spatial matches.

#### Scenario: Bin and site coordinates differ
- **WHEN** a bin lies inside the bbox but its site's stored mean coordinates lie outside
- **THEN** the bin is included in bin-scoped queries and its site is counted among sites represented by selected bins
- **AND** the site is excluded from a listing explicitly scoped to site locations inside the bbox

### Requirement: Compact area overview
The area overview SHALL report bin and site counts, known capacity and missing-capacity coverage, waste-type distribution, recent service/request summaries, and coverage of available analytical datasets. It SHALL expose available observation date ranges for historical investigation and SHALL not return an unbounded raw dataset.

#### Scenario: Discover a populated area
- **WHEN** the overview reads matching bins and their related records
- **THEN** the agent receives compact counts, totals, relevant date coverage and evidence labels suitable for selecting follow-up tools

#### Scenario: Discover absent optional data
- **WHEN** population allocations or synthetic plan records are absent
- **THEN** the overview identifies their unavailable coverage without triggering a rebuild or treating absence as known zero estimates

### Requirement: Bounded raw analytical listings
Raw entity and event listings SHALL use deterministic pagination with a default limit of 50 and a maximum of 100. Results SHALL identify returned count, effective limit, offset and whether more records exist. ID batches SHALL be limited to 100. Oversized output or grouped results SHALL identify truncation or pagination rather than imply completeness.

#### Scenario: List a dense area's bins
- **WHEN** the area contains more bins than the requested page size
- **THEN** the result contains at most that many bins in deterministic order and indicates further records

#### Scenario: Exceed a limit
- **WHEN** a caller requests more than 100 raw rows or IDs
- **THEN** the call returns a structured validation error without executing an unbounded query

### Requirement: Bin summaries and investigative listings
Tools SHALL support bin details, bounded ID lookup, counts and capacity statistics grouped by waste type, current carrier or object group. Listings SHALL support largest-capacity, missing-history, recently serviced and not-serviced-since investigations with explicit successful-service and unknown-history meanings.

#### Scenario: Investigate bins without service evidence
- **WHEN** the agent requests bins not successfully serviced since a cutoff
- **THEN** results distinguish bins whose last successful attempt predates the cutoff from bins with no recorded successful attempt
- **AND** no-history bins are not described as proven overdue

### Requirement: Site summaries reflect selected-bin membership
Tools SHALL support site details, bounded site listings and site summaries ranked by selected-bin count or known capacity, with waste-type/carrier breakdowns and service/request activity. Member bins outside the selected bbox SHALL not silently inflate area-scoped site totals.

#### Scenario: A site crosses the selected boundary
- **WHEN** a site has two selected bins and three outside the bbox
- **THEN** its area activity summary counts the two selected bins and identifies the scope
- **AND** whole-site details distinguish their five-bin membership from the selected subset

### Requirement: Historical service summaries and failure investigation
Tools SHALL support bounded attempt history, successful and failed attempt counts, latest attempt and latest successful attempt, failure reasons and grouped service summaries. Success rate SHALL be successful recorded attempts divided by all recorded attempts in the same scope and period, with numerator and denominator returned.

#### Scenario: Calculate a service-attempt success rate
- **WHEN** a period contains eight successful attempts and two failed attempts
- **THEN** the summary returns numerator 8, denominator 10 and success rate 0.8
- **AND** the result does not claim a schedule-completion or unique-bin service rate

#### Scenario: No recorded attempts
- **WHEN** the selected scope has no attempts in the requested period
- **THEN** attempt counts are zero and success rate is null with missing-evidence feedback

### Requirement: Fill observations preserve scale and missingness
Observed fill tools SHALL report the 0–3 category distribution, non-NULL observation count and missing count. An average SHALL be labelled as an ordinal category mean, never a percentage or volume. NULL fill values SHALL not enter the distribution or mean as zero.

#### Scenario: Analyze partly missing fill data
- **WHEN** four attempts have fill values 0, 2, NULL and NULL
- **THEN** the distribution counts one category 0 and one category 2, reports two observed and two missing values, and returns category mean 1

#### Scenario: Imported history has no fill observations
- **WHEN** every matching attempt has NULL fill
- **THEN** the result identifies zero observed fill values and an unavailable mean rather than empty bins

### Requirement: Resident-request investigation
Tools SHALL support request counts, bounded per-bin requests, rankings, grouped counts and trends. Requests SHALL be identified as submissions rather than unique residents or verified fill. Requests since service SHALL use the latest successful recorded attempt and report an unknown service baseline when none exists.

#### Scenario: Count repeated submissions
- **WHEN** two submissions target the same bin at the same timestamp
- **THEN** the request count is two without a claim that two distinct residents submitted them

#### Scenario: A later failed attempt exists
- **WHEN** a successful attempt is followed by a failed attempt and then a request
- **THEN** the since-service baseline remains the successful attempt and the result identifies its timestamp

#### Scenario: No successful attempt exists
- **WHEN** a bin has requests but no recorded successful attempt
- **THEN** requests since last successful service are unavailable and total requests remain separately reportable

### Requirement: Explicit local-time analytical windows
Tools SHALL return the effective period and timezone semantics. Timestamped observations SHALL use half-open local wall-clock ranges without silently assigning UTC. Calendar-day data SHALL use corresponding date ranges. Omitted periods SHALL use the run's recent window; explicit older or all-history windows SHALL remain available and SHALL not mix future plans into observed activity.

#### Scenario: Apply the default recent period
- **WHEN** a run starts on local calendar date D without an explicit period
- **THEN** observations are selected from midnight on D minus 29 days up to the captured run-start time
- **AND** calendar-day records are selected from D minus 29 days through D, with the current day identified as partial where relevant

### Requirement: Bounded day week and month trends
Tools SHALL support day, week and month trends for service attempts, failures, fill observations and resident requests. Buckets SHALL identify their period, denominator and missingness. A request exceeding 366 buckets SHALL return guidance to narrow its dates or use a coarser interval.

#### Scenario: Request an excessively detailed history
- **WHEN** a multi-year daily trend would exceed 366 buckets
- **THEN** the result requests a narrower range or weekly/monthly aggregation rather than returning unbounded data

#### Scenario: Bucket has no observed fill
- **WHEN** a service-trend bucket has attempts but no non-NULL fill values
- **THEN** its attempts are counted and its fill mean remains null

### Requirement: Polygon context uses actual spatial intersection
Geographic tools SHALL identify stored districts and service zones intersecting the bbox and summarize matching bin locations within them. Polygon holes SHALL be respected. Boundary membership SHALL be deterministic; multiple matches SHALL be resolved by lowest stored ID and reported as ambiguous coverage.

#### Scenario: Overlapping envelopes do not imply intersecting geometry
- **WHEN** a bbox overlaps a polygon's envelope but lies wholly within its hole or outside its actual shape
- **THEN** that polygon is not reported as spatially intersecting the bbox

#### Scenario: A bin lies on a shared boundary
- **WHEN** a bin is covered by two boundary polygons
- **THEN** grouped summaries assign it once using the lowest ID and report the ambiguous match count

### Requirement: Population context intersects polygons with selected bins
Population tools SHALL match selected bin coordinates to covering source polygons, respecting holes and deterministic boundary membership. They SHALL expose polygon density, suppression, missingness and grouped selected-bin counts. Full-polygon resident estimates SHALL not be presented as residents inside the bbox or multiplied by each matching bin.

#### Scenario: Several bins share one population polygon
- **WHEN** three selected bins match one polygon with an estimated resident total of 100
- **THEN** the result identifies three bins and one polygon, and never reports 300 residents from duplicating the polygon total
- **AND** the 100 estimate is labelled as applying to the full source polygon

#### Scenario: A bin lies inside a polygon hole
- **WHEN** a selected bin is inside an interior hole
- **THEN** it is not assigned that polygon merely because it lies within its envelope

#### Scenario: Stored polygon geometry is invalid
- **WHEN** a candidate source polygon has invalid geometry
- **THEN** the tool excludes it without repairing or modifying stored data and identifies its unavailable geometry
- **AND** unmatched membership is qualified as no valid covering geometry, since invalid candidates can conceal membership

### Requirement: Population allocations remain separate estimates
Tools SHALL expose existing per-bin resident allocations as estimates separate from spatial polygon membership. Allocations SHALL be grouped by waste type when aggregated, and SHALL not be summed across streams as unique residents. Missing allocations and suppressed/missing source density SHALL retain their uncertainty.

#### Scenario: Population serves multiple waste streams
- **WHEN** estimated allocations assign the same population separately to mixed-waste and glass bins
- **THEN** those totals are reported per stream without a combined unique-resident total

#### Scenario: Stored source placeholder is zero
- **WHEN** a source polygon has null density, suppression false and stored residents zero
- **THEN** its resident estimate is unavailable rather than presented as a known zero population

### Requirement: Planned collections remain distinct from observations
Schedule tools SHALL summarize and list stored planned collection dates for selected bins, including explicit future periods when requested. Planned dates SHALL not imply completed service, complete plan coverage or a verified missed collection when observation coverage is unknown.

#### Scenario: A planned date has no recorded attempt
- **WHEN** a scheduled bin has no recorded attempt on its planned date
- **THEN** the result reports the plan/observation gap without asserting a proven missed service

### Requirement: Synthetic daily outcomes have separate metrics
Tools SHALL summarize or trend stored `bin_days` outcomes using their synthetic statuses and copied/estimated field meanings. They SHALL report row and distinct-bin coverage, and SHALL not merge simulated success/failure rates with rates from recorded attempts.

#### Scenario: Compare simulation and observations
- **WHEN** both synthetic daily outcomes and recorded attempts are queried for a period
- **THEN** each result identifies its evidence type and separate denominator, and no combined service-quality rate is returned

### Requirement: Stored mock predictions preserve their own scale
Tools SHALL read stored collection-plan stops and selected stop-bin entries as mock predictions with 0–4 predicted-fill categories. Stored whole-stop totals SHALL be distinguished from recomputed selected-bin capacity subtotals. No read SHALL generate a prediction or rebuild a plan.

#### Scenario: Read a partly selected stop
- **WHEN** a stored stop includes bins inside and outside the bbox
- **THEN** its selected entries are distinguished from the full planning-time totals
- **AND** predicted category 4 is not interpreted as a recorded `bin_hist` fill category

### Requirement: Facility discovery and proximity are contextual
Tools SHALL support facility details, bounded bbox discovery and nearest-facility lookup by coordinate or bbox. Results SHALL identify distance basis and coordinate quality. Distances SHALL be geometric estimates, never road distances, travel times or evidence of a carrier's disposal route.

#### Scenario: Find a nearby facility outside the area
- **WHEN** the nearest facility lies outside the selected bbox
- **THEN** it can be returned as external context with an explicit approximate distance basis and its recorded coordinate quality

### Requirement: Cross-dataset investigations avoid inflated counts
Tools SHALL support per-bin/site/carrier/waste-type service and request comparisons, high-request/low-service rankings and high-failure rankings. Related event datasets SHALL be aggregated without multiplying counts. Rankings SHALL return contributing metrics and sample sizes rather than unsupported causal or overdue labels.

#### Scenario: Combine multiple history and request rows
- **WHEN** one bin has three attempts and four requests
- **THEN** its combined result reports three attempts and four requests rather than twelve of each

#### Scenario: Rank bins with low service evidence
- **WHEN** bins with many requests and few successes are ranked
- **THEN** the result includes request count, attempt count, successful count, period and history coverage without claiming a proven cause

### Requirement: Global and geographic comparisons expose their baselines
Tools SHALL support broader registry, waste-type, carrier and geographic summaries and area-to-global comparisons. Comparison results SHALL identify scope, period and inclusion rules; global means all eligible stored registry data, including selected-area data. Normalized metrics SHALL retain denominators and NULL behavior.

#### Scenario: Compare request intensity
- **WHEN** selected-area and global request rates per registered bin are compared
- **THEN** both use the same observation window, include their bin denominators and identify that global includes the selected area

### Requirement: Registry attribution qualifies analytical findings
Historical records SHALL be spatially and categorically grouped using their bins' current registry values, with that limitation identified. Carrier-grouped results SHALL not claim the carrier performed recorded attempts. Client counts SHALL remain address-list counts, and capacity units SHALL retain their unverified m³ assumption.

#### Scenario: Attribute service attempts by carrier
- **WHEN** a carrier performance summary groups attempts through current bin metadata
- **THEN** its result identifies current registry attribution rather than recorded historical servicing responsibility

### Requirement: Missing evidence is distinct from failed reads
Structured results SHALL distinguish zero matching records, missing values, unavailable optional coverage, invalid parameters and failed queries. Ratios with zero denominators and statistics with no known values SHALL be null. Unknown categories SHALL remain represented rather than dropped.

#### Scenario: Aggregate unknown capacities
- **WHEN** an area contains bins whose capacities are all NULL
- **THEN** known-capacity coverage is zero and total/average capacity are unavailable rather than a claimed zero capacity

#### Scenario: Preserve an unknown group
- **WHEN** some bins have no carrier or an unexpected waste-type value
- **THEN** their counts remain included in explicit unknown/source-value groups

### Requirement: Analytical reads use stored sources without rebuilding
Tools SHALL read only existing database tables and relationships. They SHALL not fetch source files or external data, import missing records, rebuild derived tables or assume route/history relationships absent from storage. Optional datasets can be absent without making the underlying bin registry unavailable.

#### Scenario: Read without development source files
- **WHEN** stored population polygons exist but the original GeoJSON is unavailable
- **THEN** population context can still be queried without a rebuild or source-file access

#### Scenario: Request unavailable historical attribution
- **WHEN** a query would require service duration or historical truck identity absent from the schema
- **THEN** no fabricated metric is exposed
