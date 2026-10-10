# Proposal

## Why

The synthetic fill-rate generator needs to know how many people put waste into each bin. Today `bin_days` has only the bin's capacity and object group, which say nothing about demand. Vilnius publishes the number of residents per hectare (`backend/data/population_density_1ha.geojson`). That lets us estimate demand per bin from real population data instead of inventing it.

## What Changes

- Load the population grid into a new `population_cells` table, with one row per source polygon:
  - The source value `gyv_sk_1ha` is a **density per hectare**. Neighbouring 1 ha cells with the same value are merged into larger polygons (up to 22 ha), so the residents of a polygon are density × area in hectares.
  - `"<11"` (suppressed for privacy, 7,508 polygons) counts as **5 per ha**. This is an assumption and can be changed with an option.
  - A null value counts as 0 residents. One null polygon is the 632 km² remainder outside the grid.
  - Current file: 14,079 polygons, about 544k residents.
- New derived table `bin_population`, with one row per bin:
  - `population_cell_id`: the polygon that contains the bin's location.
  - `resident_factor`: the estimated number of residents served by the bin.
- How `resident_factor` is computed, for each waste type:
  - Every populated polygon gives its residents to the **nearest residential collection point**. A collection point is the bins of that waste type at the same coordinates.
  - The residents are split among that point's bins by capacity.
  - Non-residential bins (commercial, legal entities, public places and institutions, unknown group) and bins with zero capacity get **0**. The generator gives them an assumed baseline fill rate, which is outside this change.
- Both values are rebuilt by a new manual command, `python -m app.interfaces.bin_population`. The command reports how many residents were allocated and the factor distribution for each waste type.
- `bin_days` gets two new columns, `population_cell_id` and `resident_factor`, copied from `bin_population` at rebuild time like the other bin attributes. **BREAKING** (for the calendar contract): the `bin_days` rebuild now refuses to run when an included bin has no `bin_population` row.
- A CSV import that replaces `bins` also empties `bin_population`. It already does this for `bin_days`.

## Capabilities

### New Capabilities

- `bin-resident-allocation`: loads the population grid, assigns each bin to its polygon, estimates the residents each bin serves, and provides the rebuild command, its output and its assumptions.

### Modified Capabilities

- `bin-day-calendar`: rows carry `population_cell_id` and `resident_factor`. The rebuild requires a current resident allocation. The calendar's allowed inputs now include the allocation.
- `table-csv-import`: replacing `bins` also empties the derived resident allocation and names the command that refills it.

## Impact

- **Code**:
  - new `backend/app/interfaces/bin_population/` (command and allocation logic)
  - `backend/app/infrastructure/models.py` (`PopulationCell`, `BinPopulation`, `BinDay`)
  - new Alembic migration `0012`
  - `backend/app/interfaces/bin_days/cli.py` (join and precondition)
  - `backend/app/interfaces/table_import/cli.py` (`BIN_DERIVED_TABLES`)
- **Dependencies**: none. Point-in-polygon and nearest-point search are written in plain Python, and the database stays plain PostgreSQL without PostGIS.
- **Data**: the GeoJSON is git-ignored like the CSV exports, so each developer must place it in `backend/data/`.
- **Docs**:
  - README: the steps to refill data are now import, then bin population, then bin days
  - `docs/` gets a verification note
- **Consumers**: the future fill-rate generator reads `resident_factor` from `bin_days`. The value is **estimated** from population data, not observed.
- **Assumptions** (also stated in the spec):
  - People use the nearest residential collection point of each waste type.
  - A merged polygon is allocated as a whole, from its centroid.
  - `"<11"` = 5 per ha.
  - The list of residential object groups is fixed.
  - Declared residence matches actual residence.
- **Uncertainties**:
  - Isolated residential points can take very large catchments: the max is about 7,600 residents and the median for an apartment 1.1 m³ bin is about 37. We accept this for now. The command prints p99 and max so outliers are visible.
  - About 29% of residential mixed-waste bins get 0, mostly small bins that share a point with larger ones or that no polygon is nearest to.
