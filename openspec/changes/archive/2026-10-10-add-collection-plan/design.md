# Design

## Context

See proposal.md for motivation and specs/collection-plan/spec.md for behaviour.

Relevant current state:
- `bins.site_id` links each bin to a site, and `bins.waste_carrier` is nullable text. Four carriers occur ("Kauno švara", "Biomotorai", "Ecoservice", "Ekonovus"). `bins.capacity_m3` is nullable.
- Derived tables (`bin_days`, `bin_population`) are rebuilt by explicit `python -m app.interfaces.<name>` commands with argparse, `Settings()` + `create_database_engine`, one transaction, a printed summary and exit codes 0/1. See `app/interfaces/bin_days/cli.py`.
- `table_import` runs a plain `TRUNCATE` (no `CASCADE`) on replaced tables, plus the tables listed in `BIN_DERIVED_TABLES` when `bins` is replaced. A new table with a foreign key to `bins` or `sites` therefore *must* be added there, or importing `bins` would fail.
- `app/ml/` and `app/optimization/` are empty packages reserved for these concerns.
- The latest migration is `0013_manual_collection_management.py`.

## Goals / Non-Goals

**Goals:**
- A stable predictor contract so the mock can be swapped for the model without touching plan building, storage or the read function.
- A stored, reproducible plan that routing reads with one Python call.

**Non-Goals:**
- Truck assignment, stop ordering, waste-type compatibility between trucks and bins.
- HTTP endpoint, frontend, map layer.
- Any use of `bin_schedule`, `bin_hist` or `bin_days` in the mock.
- Keeping several plan versions per date (the plan is rebuilt in place).

## Decisions

### 1. Predictor contract: `predict_fill_levels(session, day) -> dict[int, int]`
Lives in `app/ml/fill_prediction.py`. It returns `{bin_id: fill_level}` for every stored bin, with levels 0-4. The mock reads `SELECT id FROM bins ORDER BY id` and draws `random.Random(f"collection-plan:{day.isoformat()}").randint(0, 4)` per bin in ID order. It takes the session so the real model can load features (`bin_days` etc.) the same way.
- *Why a plain function, not a class or registry:* there will be one model (per the project principles), so the swap is an edit of this one function. A protocol or plugin layer would be speculative.
- *Alternative considered:* a `bin_predictions` table filled by the model as a separate step. Rejected for now: it adds a second command and table before the model exists. If model inference turns out to be slow or offline, the function can read from such a table later without changing the callers.
- *Seed scope:* the stream depends on the whole ordered bin list, so adding a bin can shift others' values. This is acceptable for a mock. Determinism only has to hold for unchanged bins (as the spec says).

### 2. Storage: `collection_stops` + `stop_bins`
```
collection_stops                         stop_bins
  id            bigint identity PK         stop_id        bigint FK -> collection_stops.id ON DELETE CASCADE
  date          date NOT NULL              bin_id         bigint FK -> bins.id ON DELETE CASCADE
  waste_carrier text NULL (= unassigned)   predicted_fill smallint NOT NULL CHECK 0..4
  site_id       bigint FK -> sites.id      due            boolean NOT NULL
                ON DELETE CASCADE          PK (stop_id, bin_id)
  overall_volume_m3          numeric NOT NULL     index (bin_id)
  overall_predicted_fill_m3  numeric NOT NULL
  UNIQUE NULLS NOT DISTINCT (date, waste_carrier, site_id)
  index (date)
```
- *Scope of a stop:* the truck empties every bin of its carrier at the site, so `stop_bins` holds all bins with that `(waste_carrier, site_id)` (for unassigned, all bins without a carrier at the site), each with its `predicted_fill` and a `due` flag (`predicted_fill > threshold`). A stop exists only when at least one of them is due. Roughly 2.5 times more `stop_bins` rows than due bins (about 22k rows at most for 21.7k bins), which is small.
- *Migration:* `0014_collection_plan.py` has not shipped, so it is edited in place (no new migration). Local databases that already ran it need `alembic downgrade -1` before the edit is picked up, then `upgrade head`.
- `NULLS NOT DISTINCT` makes the uniqueness hold for unassigned stops too. The compose image is `postgres:17-alpine`, and the option is supported since 15.
- `overall_volume_m3` (sum of `capacity_m3` over all the stop's bins, missing = 0) and `overall_predicted_fill_m3` (sum of `capacity_m3 * share(predicted_fill)`) are stored, not computed when read, so routing gets the values from the moment of planning. They aren't recalculated after a bin deletion (acceptable, and the spec says so).
- *Fill shares (assumption):* level 0 = 0.2, 1 = 0.5, 2 = 0.8, 3 = 1.0, 4 = 1.5 of capacity (above 1.0 means over-full). They are defined once as a constant next to the plan building in `app/services/collection_plan.py`, because they translate the predictor's levels into volumes and do not belong to the predictor itself. The arithmetic stays in SQL on `numeric`, so there are no rounding artefacts (0.6 m3 at level 2 gives exactly 0.48).
- Unassigned is `NULL` in storage and becomes a distinct group key in the read result. A sentinel string such as `"unassigned"` in the column was rejected because it could collide with a real carrier name.
- Stops left without a due bin after a bin deletion: the read query skips stops that have no `stop_bins` row with `due`. This avoids a trigger.

### 3. Plan building in SQL, inside one transaction
`app/services/collection_plan.py`:
- `build_plan(session, day, threshold) -> summary`: gets predictions from the predictor. Then it stages **every** `(bin_id, fill, due)` triple into a temp table (`ON COMMIT DROP`, like `bin_days`), runs `DELETE FROM collection_stops WHERE date = :day` (cascade removes `stop_bins`), and inserts one stop per `(waste_carrier, site_id)` that has a due bin. The stop's totals come from aggregating **all** staged bins of that `(waste_carrier, site_id)`: `SUM(COALESCE(capacity_m3, 0))` and `SUM(COALESCE(capacity_m3, 0) * share(fill))`, with `share` as a `CASE` over the fill levels. Last, it inserts `stop_bins` for all staged bins by joining on `(waste_carrier, site_id)` and commits. Joins on the carrier use `IS NOT DISTINCT FROM`, so unassigned bins match.
- All bins are staged (about 21.7k rows), because the totals need the fill level of the bins that are not due. That fits in memory with a simple `executemany`/COPY, no batching concerns.
- `SET LOCAL lock_timeout = SYNC_LOCK_TIMEOUT_MS` as the other rebuild commands do.
- *Alternative considered:* grouping in Python with ORM inserts. That's fine too, but SQL grouping is shorter and matches `bin_days`.

### 4. Read: `get_plan(session, day, carriers=None) -> dict[str | None, list[dict]]`
Same service module. Keys are carrier names, and `None` holds unassigned stops. Python's `None` is the natural key here because routing calls this function directly. If carriers are given, every requested carrier is present as a key, with an empty list when it has no stops. To ask for the unassigned group, pass `None` in `carriers`. Each stop dict has `stop_id`, `site_id`, `address`, `latitude`, `longitude`, `overall_volume_m3` and `overall_predicted_fill_m3` (`Decimal`), and `bins: [{bin_id, waste_type, capacity_m3, predicted_fill, due}]` for all the stop's bins. Stops with no due bin are skipped. Stops are sorted by site_id and bins by bin_id, so results are deterministic.

### 5. CLI: `python -m app.interfaces.collection_plan [--date YYYY-MM-DD] [--threshold N]`
`app/interfaces/collection_plan/{__init__,__main__,cli}.py`, which mirrors `bin_days`. It validates arguments before connecting, opens a session from `Settings()`, calls `build_plan` and prints the summary. It catches `SQLAlchemyError` and logs a message without credentials, like the existing CLIs. "Today" is the container's local date (`date.today()`).

### 6. CSV import integration
Add `"collection_stops"` and `"stop_bins"` to `BIN_DERIVED_TABLES` with the refill command `python -m app.interfaces.collection_plan`. The existing logic then truncates them, without CASCADE, together with `bins` when `bins` is replaced and reports the refill command. A `stop_bins` file without a `collection_stops` file is unlikely, and it's handled by the existing reference check.

## Risks / Trade-offs

- [Mock values are uniform random, so about 40% of bins are due daily at threshold 2, which is unrealistic] → The summary and README label it as mock data. The threshold can be raised for smaller demo plans. Realism comes with the model.
- [Predictor contract may need more fields later, such as confidence or predicted volume] → The return type is internal Python. Extending it means adding a `stop_bins` column and a migration, with no API to version.
- [`date.today()` in a UTC container differs from Vilnius time around midnight] → Accepted. The `--date` argument overrides it.
- [Stored totals go stale after a bin edit] → Documented. Rebuild the date.
- [`stop_bins` mixes due and non-due bins, so consumers that want only due bins must filter on `due`] → The flag is explicit in the read result; the totals need the non-due bins, and storing them avoids a second query for routing.
- [The fill-to-share table is an assumption, so `overall_predicted_fill_m3` is only as good as it] → Stated in the spec and README; one constant to change.

## Migration Plan

New migration `0014_collection_plan.py` that creates both tables. Downgrade drops them. There are no data migrations, and the tables start empty until the command runs.
