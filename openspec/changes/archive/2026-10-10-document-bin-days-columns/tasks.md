# Tasks

## 1. Data dictionary

- [x] 1.1 Create `docs/bin-days-columns.md` with the row grain (one row per eligible bin per date), the primary key `(bin_id, date)`, the cascade delete from `bins`, and a summary table (name, SQL type, null, kind) for all 17 columns. Take types and nullability from `BinDay` in `backend/app/infrastructure/models.py`. Verify that the table has 17 rows and that each type and null value matches the model.
- [x] 1.2 Add one section per column with meaning, source, units or values, and generator notes. The calendar columns get ISO and season definitions. `bin_id`, `site_id`, `waste_type`, `capacity_m3`, `sub_district` and `object_group` each get their own entry, with the unverified m³ assumption and the snapshot-at-rebuild note. `population_cell_id` and `resident_factor` get their meaning and their estimated status. The four synthetic columns get exact windows, and `collection_status` gets its complete value set. Verify that every column has a section.
- [x] 1.3 List the observed `waste_type` and `object_group` values with counts, labelled as values from `bins_202610091935.csv` that the database does not enforce. Verify the counts with `SQL "select waste_type, count(*) from bins group by 1"` and the same query for `object_group`.

## 2. Single source and pointers

- [x] 2.1 In the README "Bin-day calendar" section, replace the column table and the `collection_status` value list with a link to `docs/bin-days-columns.md`, and keep the run instructions, options, eligibility, replacement and assumptions. Verify that no `bin_days` column table is left in `README.md` and that the link resolves.
- [x] 2.2 Add a sentence to the `BinDay` model docstring that names `docs/bin-days-columns.md` as the place to document columns. Verify that the backend still imports with `uv run python -c "import app.infrastructure.models"` from `backend/`.

## 3. Verification

- [x] 3.1 Compare the documented columns with the live schema: `SQL "select column_name from information_schema.columns where table_name = 'bin_days' order by 1"` against the column names in the summary table. Verify that both lists are identical (17 names).
