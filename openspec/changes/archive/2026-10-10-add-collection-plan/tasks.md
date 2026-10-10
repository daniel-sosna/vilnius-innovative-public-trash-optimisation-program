# Tasks

## 1. Schema

- [x] 1.1 Update `CollectionStop` (rename `volume_m3` to `overall_volume_m3`, add `overall_predicted_fill_m3`, both `numeric NOT NULL`) and `StopBin` (add `due` boolean NOT NULL) in `backend/app/infrastructure/models.py` as in design Decision 2 (FKs with `ON DELETE CASCADE`, `UNIQUE NULLS NOT DISTINCT (date, waste_carrier, site_id)`, `predicted_fill` check 0..4, indexes on `date` and `stop_bins.bin_id`, comment marking `predicted_fill` as predicted/mock data); verify the models import without error
- [x] 1.2 Edit migration `backend/alembic/versions/0014_collection_plan.py` in place (no new migration) to create both tables with the new columns; first run `alembic downgrade -1` with the old version, then edit; verify `alembic upgrade head`, `alembic downgrade -1` and `upgrade head` again all succeed and `\d collection_stops` and `\d stop_bins` show the new columns and the unique constraint

## 2. Prediction source

- [x] 2.1 Create `backend/app/ml/fill_prediction.py` with `predict_fill_levels(session, day) -> dict[int, int]` (mock: date-seeded uniform 0..4 per bin in ID order, docstring stating it is the contract the real model must fulfil); verify two calls for the same date return identical dicts covering every bin and a different date differs

## 3. Plan service

- [x] 3.1 Update `backend/app/services/collection_plan.py` `build_plan(session, day, threshold)` per design Decision 3: stage every bin's fill level with its due flag, create stops for carrier/site pairs with a due bin, compute `overall_volume_m3` and `overall_predicted_fill_m3` over all of the pair's bins (fill shares 0.2/0.5/0.8/1.0/1.5 as one constant), store all those bins in `stop_bins` with `due`, replace the date in one transaction, and return the summary counts (bins evaluated, due bins, stops per carrier, unassigned stops, bins without capacity among the stops' bins); verify with SQL that every due bin is in exactly one stop flagged due, a stop's bins are exactly the carrier's bins at its site, totals equal the sums of capacities and of capacity times share, and another date's rows are untouched
- [x] 3.2 Update `get_plan(session, day, carriers=None)` per design Decision 4 (`None` key for unassigned, requested carriers always present, stops without a due bin skipped, new total keys and a `due` key on each bin, deterministic order); verify from a Python shell that all-carrier and filtered reads return the expected groups and a date without a plan returns `{}`

## 4. Command and import integration

- [x] 4.1 Check `backend/app/interfaces/collection_plan/cli.py` against the summary wording in the spec ("bins without capacity among the bins of the stops") and adjust it; verify a valid run exits 0 and `--threshold 5`, `--date 2026-13-01` and an empty `bins` table exit 1 without changes
- [x] 4.2 Add `collection_stops` and `stop_bins` to `BIN_DERIVED_TABLES` in `backend/app/interfaces/table_import/cli.py` with the refill command; verify that a `sites`+`bins`+`bin_hist` import succeeds with a stored plan, empties both tables and names the command, and that a `bin_hist`-only import keeps the plan
- [x] 4.3 Update the README section "Collection plan" (stop contents: all of the carrier's bins at the site, `due` flag, the two totals, the fill shares assumption, `get_plan` keys) and `docs/collection-plan-verification.md` (volume and predicted-fill checks, due flag, the 0.6 m3 at level 2 example); verify each documented command runs as written against imported data

## 5. End-to-end check

- [x] 5.1 With the CSV exports imported, run the command for today with the default threshold, rerun with `--threshold 3`, delete a stop's only due bin, and read the plan for two carriers plus unassigned via `get_plan`; verify the results match the spec scenarios (reproducible plan, replaced date, totals including non-due bins, removed stop without a due bin, empty group for a carrier without stops)
