# Design

## Context

- `bin_days` is a derived table rebuilt by `python -m app.interfaces.bin_days` ([cli.py](../../../backend/app/interfaces/bin_days/cli.py)). It copies static bin attributes (`site_id`, `waste_type`, `capacity_m3`, `sub_district`, `object_group`) through the join in `INSERT_SQL`. `site_id` is stored without a foreign key.
- `table_import` replaces `bins` with `TRUNCATE` followed by `COPY` of the CSV's own columns. It empties the tables listed in `BIN_DERIVED_TABLES` and names the command that refills each one ([cli.py](../../../backend/app/interfaces/table_import/cli.py)). Extra derived columns on `bins` would therefore be NULL after every import.
- The database is plain `postgres:17-alpine`, with no PostGIS. The backend has no numeric or geometry libraries.
- Measurements on the current data (exploration, 2026-10-10):
  - Density file: 14,079 `Polygon` features in CRS84. 11,901 are 1 ha. The rest are merged cells of 2–22 ha that share one value. Values: 6,471 numeric (11–423), 7,508 `"<11"`, 100 null. Feature 14079 is a 632 km² remainder with 149 holes. Total residents with `"<11"` = 5 is about 544k.
  - Every one of the 21,951 bins falls in exactly one polygon. 4,466 of them fall in null polygons, mostly the remainder.
  - 13,632 bins have coordinates that differ from their site's: p50 5 m, p90 56 m, max 1.7 km. Sites are address groups, not physical points.
  - Allocating residents only within the bin's own polygon reaches 57.7% of residents. The nearest-residential-point allocation gives a median of about 37 residents for a 1.1 m³ apartment bin. Polygon centroid to point: p50 120 m, p90 320 m.
  - 3 bins have capacity 0.

## Goals / Non-Goals

**Goals:**
- One command, run in seconds, that loads the polygons and computes every bin's polygon and resident factor in one all-or-nothing transaction.
- `bin_days` exposes both values without the generator having to know about polygons.

**Non-Goals:**
- Baseline fill rates for non-residential bins. These belong to the generator.
- Smoothing large catchments, for example with a radius or distance decay. We will revisit if the printed p99 and max show outliers that cause problems.
- Serving polygons or factors through the API or UI.
- Splitting merged polygons back into 1 ha cells.

## Decisions

### 1. Two new tables, nothing added to `bins`

```
population_cells                          bin_population
  id INTEGER PK (= OBJECTID)    <----FK---- population_cell_id INTEGER NULL
  density_per_ha INTEGER NULL               bin_id BIGINT PK -> bins.id ON DELETE CASCADE
  suppressed BOOLEAN NOT NULL               resident_factor DOUBLE PRECISION NOT NULL >= 0
  area_ha DOUBLE PRECISION NOT NULL
  residents DOUBLE PRECISION NOT NULL       (assumed density already applied)
  min_lon, min_lat, max_lon, max_lat DOUBLE PRECISION
  geometry JSONB NOT NULL                   (GeoJSON coordinates: rings incl. holes)
```

`population_cells` holds the source data, which the user asked to have as a table so it can be queried. `bin_population` is derived and depends on the cells, on every bin and on the options, so it gets rebuilt like `bin_days` rather than living on `bins`. The foreign key `bin_population.population_cell_id` uses RESTRICT. The command truncates both tables together, so the constraint never blocks it.

*Alternatives:*
- Columns on `bins`. They would be wiped or left NULL by every CSV import and VASA sync, and a bin's factor would go stale when a neighbouring bin changes.
- Leaving out `population_cells` and keeping only the cell id. That loses the residents needed to explain or verify a factor.

### 2. Separate command, `python -m app.interfaces.bin_population`

The new command lives in `backend/app/interfaces/bin_population/`, as `cli.py` plus a pure `allocation.py` that has no database access. `bin_days` reads the result through `INNER JOIN bin_population`. Before simulating, it checks that every eligible bin has a row, so it can fail fast. The refill order is: import, then bin population, then bin days.

*Alternative:* computing the allocation inside the `bin_days` rebuild. That couples a seconds-long geometry step to a minutes-long simulation, and the calendar would need GeoJSON options.

### 3. Geometry in plain Python

- **Point in polygon**: ray casting on the outer ring, excluding holes. A uniform grid index of about 0.01° on the polygon bounding boxes keeps it to a few candidates per bin. When a bin matches several polygons (shared edges), the lowest id wins.
- **Polygon centroid**: the area-weighted centroid of the outer ring (shoelace formula). Only polygons with residents greater than 0 need one. Those polygons are compact grid unions, which keeps the centroid close to the polygon. The remainder polygon is null and gets skipped.
- **Distance**: equirectangular approximation in metres:
  - `dx = Δlon · cos(54.7°) · 111,320`
  - `dy = Δlat · 111,320`
  - The error across Vilnius is below 0.5%.
- **Nearest point**: a grid index of collection points per waste type, searched in growing rings until the best distance is below the ring radius. Ties go to the point whose smallest bin id is lowest.

Measured in pure Python during exploration: about 1 s for the point-in-polygon pass and a few seconds for the nearest-point search over three waste types.

*Alternatives:*
- PostGIS. It needs a new image and extension for two queries.
- shapely or scipy. They add dependencies the backend otherwise doesn't need.

### 4. Collection point = identical bin coordinates per waste type

A collection point groups the residential bins of one waste type that have exactly the same stored latitude and longitude. `site_id` is not used, because a site can group bins up to 1.7 km apart.

### 5. Storing the residents with the assumption applied

`population_cells.residents` stores density × area with the `--suppressed-density` value already applied. `density_per_ha` stays NULL and `suppressed` true for `"<11"`. That way an analyst can recompute with another assumption, while the generator and verification get one ready number. The summary prints the density that was used.

### 6. `bin_days` columns

- Migration `0012` creates both new tables.
- It runs `TRUNCATE bin_days`, as in `0011`, because the new column is NOT NULL.
- It adds `population_cell_id INTEGER NULL` (no FK, like `site_id`, so reloading the cells never blocks on calendar rows) and `resident_factor DOUBLE PRECISION NOT NULL CHECK (resident_factor >= 0)`.
- `INSERT_SQL` joins `bin_population` and copies both.
- Cell ids are the source `OBJECTID`s, so they stay stable across reloads of the same file.

### 7. CSV import

Add `"bin_population": "python -m app.interfaces.bin_population"` to `BIN_DERIVED_TABLES`. `population_cells` does not reference `bins`, so the import keeps it.

## Risks / Trade-offs

- [A lone residential point takes a whole neighbourhood, with a factor of thousands] → p99 and max are printed on every run. If it matters for the generator, add a distance cap or switch to a radius split (option D from exploration) without changing the table contract.
- [Commercial bins that serve residents in practice get 0] → The generator's per-group baseline covers them. The residential group list is one constant that is easy to adjust.
- [Merged polygons up to 22 ha are allocated whole from their centroid] → Merged polygons are mostly low-density `"<11"`, so the residents involved are few.
- [Stale factors after a sync adds or removes bins] → `bin_days` refuses to rebuild when a bin has no allocation. Removed bins only shift their neighbours' share until the next rebuild. Documented in the README.
- [Declared residence differs from actual residence (students, temporary residents)] → Accepted. This is the best open data available.
- [The density file is not in git] → The README lists it next to the CSV exports. A missing file makes the command fail with the path in the message.

## Migration Plan

1. `alembic upgrade head` runs at startup and applies `0012`. This empties `bin_days`.
2. Run `python -m app.interfaces.bin_population`.
3. Rebuild `bin_days` with the usual dates.

Rollback: downgrading `0012` drops the two `bin_days` columns and both new tables. `bin_days` then needs a rebuild.
