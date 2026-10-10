# Tasks

## 1. Schema

- [x] 1.1 Add Alembic migration `0012` (revises `0011`) per design decisions 1 and 6:
  - create `population_cells` and `bin_population` (FK to `bins` ON DELETE CASCADE, FK to `population_cells` RESTRICT, `resident_factor >= 0` check)
  - truncate `bin_days`, then add `population_cell_id INTEGER NULL` and `resident_factor DOUBLE PRECISION NOT NULL CHECK (>= 0)`
  - downgrade reverses all of it

  Verify that `alembic upgrade head`, then `downgrade 0011`, then `upgrade head` all succeed, and that `\d population_cells`, `\d bin_population` and `\d bin_days` show the columns and constraints.
- [x] 1.2 Add `PopulationCell` and `BinPopulation` models, and the two new `BinDay` columns, to `backend/app/infrastructure/models.py`. Give `bin_population` cascade relationships from `Bin`, like `schedule`. Verify that `alembic check` reports no differences.

## 2. Allocation core

- [x] 2.1 Create `backend/app/interfaces/bin_population/allocation.py`, with no database access:
  - parse and validate the GeoJSON features: `OBJECTID`, Polygon geometry, a density of digits, `"<11"` or null
  - compute residents as density × `Shape_Area`/10,000, with the suppressed density applied, and the area-weighted centroid and bounding box of each polygon

  Verify with a `python -I -c` snippet on the current file: 14,079 polygons, 7,508 suppressed, 100 null, and total residents ≈ 544k at density 5. Also check that `"14"` on 30,000 m² gives 42.
- [x] 2.2 Add bin → polygon lookup: a grid index over the bounding boxes, ray casting with holes excluded, lowest id on ties. Verify on the current bins export that all 21,951 bins get a polygon and 4,466 of them land in null-density polygons. Also check one bin inside a hole of polygon 14079 maps to the grid cell, not to 14079.
- [x] 2.3 Add the catchment per waste type (design decisions 3 and 4):
  - the residential object-group constant, with capacity > 0
  - collection points by identical coordinates
  - nearest point to each populated centroid by expanding grid search, using the equirectangular distance and the tie rule
  - factor = point residents × capacity / point capacity, and 0 for all other bins

  Verify on the current exports:
  - factors per waste type sum to total residents within 1e-6 relative error
  - mixed-waste 1.1 m³ `Daugiabučiai namai` median ≈ 37
  - the spec's 100 → 25/75 split holds on a hand-built example
  - two runs give identical output

## 3. Rebuild command

- [x] 3.1 Add `backend/app/interfaces/bin_population/` with `__init__.py`, `__main__.py` and `cli.py`:
  - options `--file` (default `backend/data/population_density_1ha.geojson`) and `--suppressed-density` (default 5, 0–10), both validated before connecting
  - one transaction under `SYNC_LOCK_TIMEOUT_MS`: load bins, compute, `TRUNCATE bin_population, population_cells`, then COPY both tables

  Verify that:
  - `--suppressed-density 11` and a missing `--file` exit with 1 and name the value or path, with the database stopped
  - a successful run stores 14,079 cells and 21,951 `bin_population` rows
  - killing the process mid-run leaves the previous contents intact
- [x] 3.2 Print the success summary required by the spec "Clear output and exit codes": polygon counts and residents, the density used, bins with or without a polygon, and per waste type the residential bins, points, allocated and unallocated residents, distance p50/p90, and factor p50/p90/p99/max. Map failures to exit 1 without credentials, as `bin_days/cli.py` does. Verify against the current exports that the totals match task 2.3 and the exit code is 0.

## 4. Calendar and import integration

- [x] 4.1 In `backend/app/interfaces/bin_days/cli.py`:
  - before simulating, count eligible bins without a `bin_population` row. If there are any, change nothing, log the count and `python -m app.interfaces.bin_population`, and exit with 1.
  - join `bin_population` in `INSERT_SQL` and copy `population_cell_id` and `resident_factor`.

  Verify that right after a CSV import the rebuild fails with 21,840 missing. After the population command, a 2026-09-09..2026-10-09 rebuild gives 672,545 rows, and every row's `resident_factor` equals the bin's `bin_population` value.
- [x] 4.2 Add `bin_population` to `BIN_DERIVED_TABLES` in `backend/app/interfaces/table_import/cli.py`. Verify that importing `sites`, `bins` and `bin_hist` empties `bin_population`, keeps `population_cells` and logs the refill command, and that a `bin_hist`-only import keeps `bin_population`.

## 5. Documentation and end-to-end check

- [x] 5.1 Update the README:
  - Add a section "Bin population (residents per bin)": the density file to place in `backend/data/`, the command and its options, the meaning of both values (**estimated** from population data), and the assumptions (nearest residential point, `"<11"` = 5, residential groups, whole merged polygons, declared residence).
  - Update the refill order in "Import table CSV exports" and "Bin-day calendar" to: import, then bin population, then bin days.
  - Add the AI-agent data check for the GeoJSON.

  Verify that the documented commands run as written.
- [x] 5.2 Add `docs/bin-population-verification.md` with SQL and command checks:
  - row counts
  - sums of factors per waste type equal `SUM(population_cells.residents)`
  - non-residential bins have 0
  - bins with a `population_cell_id` match their polygon's bounding box
  - identical output on rerun
  - the `bin_days` precondition failure

  Also add the two new columns to `docs/bin-day-calendar-verification.md`. Verify that every check passes on a fresh import → bin population → bin days run.

## Workflow follow-up

- Archive the change with `/opsx:archive` after review, and check that `openspec/specs/bin-resident-allocation/spec.md` exists and that the `bin-day-calendar` and `table-csv-import` specs contain the merged requirements.
