# bin-resident-allocation Specification

## Purpose

Estimates how many residents each bin serves from the Vilnius population-density grid. The estimate drives the demand side of synthetic fill-level generation.

## Requirements

### Requirement: Rebuild only on explicit invocation
The resident allocation, meaning the stored population polygons and the per-bin values, SHALL change only when an operator runs the bin population command. The command SHALL work inside the backend container and natively, using the existing database configuration. Application startup, migrations and idle runtime SHALL NOT build or change the allocation.

#### Scenario: Startup leaves the allocation alone
- **WHEN** the backend starts or migrations run
- **THEN** the stored population polygons and per-bin values are unchanged

### Requirement: Load population polygons from the density file
The command SHALL read a GeoJSON FeatureCollection of polygons in longitude/latitude. The default is `backend/data/population_density_1ha.geojson`, and `--file` gives another path. Each feature SHALL be stored as one population polygon whose identifier is the feature's `OBJECTID`, with its density value and its area. A rebuild SHALL replace all previously stored polygons.

#### Scenario: Current Vilnius file
- **WHEN** the command runs with the current density file
- **THEN** 14,079 population polygons are stored, identified by their `OBJECTID`

#### Scenario: Missing file
- **WHEN** the file does not exist
- **THEN** the command changes nothing, names the missing path and exits with 1

#### Scenario: Unreadable feature
- **WHEN** a feature has no `OBJECTID`, has a geometry that is not a polygon, or has a density value that is not a whole number, `"<11"` or null
- **THEN** the command changes nothing, names the feature and the problem, and exits with 1

### Requirement: Residents of a polygon
The residents of a polygon SHALL be its density per hectare multiplied by its area in hectares. A polygon can merge several neighbouring 1 ha cells that share one density value. A suppressed value `"<11"` SHALL count as an assumed density, `--suppressed-density` (default 5, between 0 and 10). A null value SHALL count as 0 residents. Resident numbers are estimates, not counts.

#### Scenario: Merged polygon
- **WHEN** a polygon has density `"14"` and an area of 30,000 m²
- **THEN** its residents are 42

#### Scenario: Suppressed density
- **WHEN** a 1 ha polygon has density `"<11"` and the default options are used
- **THEN** its residents are 5

#### Scenario: Remainder polygon
- **WHEN** a polygon has a null density, like the 632 km² remainder outside the grid
- **THEN** its residents are 0

#### Scenario: Invalid suppressed density
- **WHEN** `--suppressed-density` is negative, above 10 or not a number
- **THEN** the command changes nothing, names the bad value and exits with 1 without connecting to the database

### Requirement: Polygon of each bin
Each bin SHALL be linked to the population polygon that contains its stored location, holes excluded. A bin on a shared edge SHALL be linked to the polygon with the lowest identifier. A bin inside no polygon SHALL have no polygon. The polygon of a bin SHALL NOT affect its resident factor.

#### Scenario: Bin inside a cell
- **WHEN** a bin's latitude and longitude fall inside polygon 5123
- **THEN** its population polygon is 5123

#### Scenario: Bin in a hole
- **WHEN** a bin lies in a hole of the remainder polygon and inside the grid cell that fills that hole
- **THEN** its population polygon is that grid cell

#### Scenario: Bin outside the grid
- **WHEN** a bin's location is inside no polygon
- **THEN** it has no population polygon and still has a resident factor

### Requirement: Residential bins
A bin SHALL be residential when its object group is one of `Daugiabučiai namai`, `Dvibučiai`, `Daugiabučių/garažų bendrijos`, `Sodų bendrijos` or `Sodų/garažų bendrijos`, and its capacity is greater than 0. All other bins, including those with no object group or no capacity, SHALL NOT be residential.

#### Scenario: Commercial bin
- **WHEN** a bin's object group is `Komercinė paskirtis`
- **THEN** it is not residential

#### Scenario: Zero capacity
- **WHEN** a bin's object group is `Daugiabučiai namai` and its capacity is 0
- **THEN** it is not residential

### Requirement: Residents go to the nearest residential collection point
For each waste type separately, the residential bins of that type at identical coordinates SHALL form one collection point. All residents of each polygon SHALL be allocated to the collection point of that type nearest to the polygon's centroid, using ground distance. On equal distance, the point containing the bin with the lowest identifier SHALL win. This assumes residents use their nearest residential point.

#### Scenario: Two points nearby
- **WHEN** a polygon with 120 residents has its centroid 80 m from point A and 150 m from point B, both with mixed-waste bins
- **THEN** all 120 residents are allocated to point A for mixed waste

#### Scenario: Waste types allocated independently
- **WHEN** the nearest mixed-waste point to a polygon is A and the nearest glass point is C
- **THEN** its residents count toward A for mixed waste and toward C for glass

#### Scenario: Commercial bin nearer than residential
- **WHEN** a commercial bin is closer to a polygon than any residential bin
- **THEN** the polygon's residents go to the nearest residential point

#### Scenario: Waste type without residential bins
- **WHEN** a waste type has no residential bins
- **THEN** no residents are allocated for it and the summary reports that type's residents as unallocated

### Requirement: Resident factor of each bin
Each residential bin's resident factor SHALL be the residents allocated to its collection point multiplied by the bin's capacity and divided by the total capacity of the point's bins. A bin that is not residential SHALL have factor 0. For each waste type with at least one residential bin, the factors SHALL add up to the residents of all polygons.

#### Scenario: Split by capacity
- **WHEN** a point received 100 residents and holds two mixed-waste bins of 1.1 m³ and 3.3 m³
- **THEN** their factors are 25 and 75

#### Scenario: Point that is nobody's nearest
- **WHEN** no polygon has a given residential point as its nearest
- **THEN** that point's bins have factor 0

#### Scenario: Non-residential bin
- **WHEN** a bin's object group is `Juridiniai asmenys`
- **THEN** its factor is 0

#### Scenario: Residents are conserved
- **WHEN** the allocation is rebuilt with the current files
- **THEN** for each waste type the factors of its bins add up to the total residents of all polygons, about 544,000, within rounding

### Requirement: One allocation row per bin
After a rebuild, every stored bin SHALL have exactly one allocation, with its population polygon or none, and its resident factor. Bins whose allocation is missing are those added since the last rebuild.

#### Scenario: Current exports
- **WHEN** the command runs after importing the current 21,951 bins
- **THEN** 21,951 bins have an allocation

### Requirement: All-or-nothing replacement
A rebuild SHALL replace the stored polygons and all per-bin values together. Any failure SHALL leave the previous polygons and values exactly as they were.

#### Scenario: Failure keeps previous allocation
- **WHEN** a rebuild fails partway, for example because the connection is lost
- **THEN** the previous polygons and per-bin values remain and the command exits with 1

### Requirement: Allocation of removed bins disappears
When a bin is deleted, its allocation SHALL be deleted with it. The allocations of other bins SHALL keep their values until the next rebuild, even though their factors may now be out of date.

#### Scenario: Synchronization cleanup removes a bin
- **WHEN** a VASA synchronization cleanup deletes a bin
- **THEN** that bin has no allocation and the other bins' allocations are unchanged

### Requirement: Reproducible allocation
Two rebuilds with the same file, bins and options SHALL produce identical polygons and per-bin values.

#### Scenario: Repeated run
- **WHEN** the command runs twice without changes in between
- **THEN** both runs store identical values and report identical summaries

### Requirement: Clear output and exit codes
On success, the command SHALL report the polygon and resident totals, the suppressed density used, how many bins have a polygon, and for each waste type the residential bins, collection points, allocated and unallocated residents, polygon-to-point distance percentiles (50th, 90th) and residential factor percentiles (50th, 90th, 99th, max). It SHALL then exit with 0. On failure it SHALL exit with 1 with a readable reason that does not disclose database credentials.

#### Scenario: Successful run summary
- **WHEN** the command runs with the current files
- **THEN** it reports 14,079 polygons with the counts of suppressed and null ones, the total residents, the default suppressed density 5, the numbers of bins with and without a polygon, and the per-waste-type statistics for mixed, paper/plastic and glass waste, and exits with 0

#### Scenario: Database unavailable
- **WHEN** the database cannot be reached
- **THEN** the command exits with 1 and the message does not contain the database password
