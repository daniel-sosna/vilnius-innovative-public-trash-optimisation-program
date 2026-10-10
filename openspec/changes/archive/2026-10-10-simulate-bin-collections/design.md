# Design

## Context

- `python -m app.interfaces.bin_days` ([cli.py](../../../backend/app/interfaces/bin_days/cli.py)) rebuilds `bin_days` in a single transaction: `TRUNCATE`, then one `INSERT ... SELECT` that crosses `generate_series` with `bins` and computes the calendar features in SQL. It takes about 30 s for 31 days.
- `bin_schedule` holds one row per bin per planned date. It is the latest monthly snapshot, currently October 2026, and 21,840 bins have dates.
- The backend has no numerical dependencies (no numpy or pandas). `psycopg` 3 is available and supports `COPY`.
- Measurements from the current exports, used for the rules below:
  - Cycle fit of the October snapshot under the spec's rule: 12,279 bins weekly, 6,319 every two weeks, 2,281 daily, 67 every four weeks, 894 single-date bins (28 days), 0 fallbacks. All multi-date bins are reproduced exactly.
  - `bin_hist`: 3.4% of events are non-serviced. That includes reasons that are not carrier failures, such as "empty container". 23% of next-day events after a non-service are non-serviced too. These support "retry fails more often". The user chose the defaults 0.028, 0.40 and 0.70, so they are assumptions, not fitted values.
  - 95.5% of planned dates from 2026-10-01 to 10-09 have a history event, which supports "an attempt happens on every planned day".

## Goals / Non-Goals

**Goals:**
- One rebuild command that writes the calendar, the synthetic collection status and the three look-back features in a single all-or-nothing transaction.
- Deterministic output for a given seed, independent of bin processing order.
- Keep the existing calendar SQL and attribute copying unchanged.

**Non-Goals:**
- Fill levels. The generator still owns them and resets on `collected` or `retry_collected`.
- Calibrating probabilities per bin, district or waste type, or seasonal failure effects.
- Moving collections because of holidays, or modelling truck capacity and routes.
- Reading `bin_hist`. The calendar stays independent of observed history.

## Decisions

### 1. Simulate in Python, join attributes in SQL

The rebuild becomes:

1. Load the eligible bins and their planned dates (one query).
2. In Python, simulate every bin from `start − 35` to `end` and keep only rows from `start` on: `(bin_id, date, collection_status, holidays_since_last_collection, collections_last_28d, missed_collections_28d)`.
3. Stream those rows with `COPY` into a temporary table (`ON COMMIT DROP`) in the rebuild transaction.
4. `TRUNCATE bin_days`, then `INSERT INTO bin_days ... SELECT` from the temporary table joined to `bins`. The calendar features (`EXTRACT ...`) and the attribute columns are computed exactly as today. Truncating last keeps the exclusive lock short.

*Alternatives:*
- Pure SQL, using recursive CTEs or window functions for the retry state machine. A per-bin random state machine with retries cancelled by planned days is very hard to read and debug in SQL.
- Computing every column in Python and copying straight into `bin_days`. That duplicates the season and ISO-week logic that is already in SQL and already verified.

### 2. Per-bin state machine in plain Python, without numpy

For each bin, walk the days one by one with state `pending_retry ∈ {0, 1, 2}`:

```
for day in sim_start..end:
    if day is planned:   kind = first; pending = 0
    elif pending > 0:    kind = retry(pending)
    else:                status = none; kind = None
    if kind:
        p = min(p_kind * (holiday_factor if day is holiday else 1), 0.95)
        if rng.random() < p:   # failure
            next_is_retry = (kind != retry2) and not planned(day + 1)
            status = failed if next_is_retry else missed
            pending = next retry number if next_is_retry else 0
        else:
            status = collected if kind == first else retry_collected
            pending = 0
```

The look-back features are computed in the same pass. They describe the state at the start of the day, so they are emitted before today's outcome is applied:
- `collections_last_28d` and `missed_collections_28d`: running counts over a 28-day ring buffer.
- `holidays_since_last_collection`: a counter reset to 0 on the day after a success, plus 1 for each holiday day that passes. Before the first success it counts from the simulation start.

Volume: about 21.7k bins × 366 days ≈ 8M steps per year of range. Plain Python is a few seconds per million steps, so a one-year rebuild was expected to take tens of seconds. Measured: about 4 minutes for one year (including the `COPY` and insert), so the five-year maximum takes roughly 20 minutes. That's acceptable for an explicitly run offline command. Rows are streamed to `COPY` per bin instead of being held in memory all at once.

*Alternative:* vectorising with numpy. That adds a dependency, and the sequential retry state is awkward to vectorise. Not worth it at this size.

### 3. Reproducibility: one RNG per bin

Each bin uses `random.Random(f"{seed}:{bin_id}")`. A string seed is hashed the same way across runs and platforms. The outcomes therefore depend only on the seed, the bin, its schedule, the range start and the parameters, not on query order or on which other bins exist. The default seed is 42, so a plain rerun reproduces the same data, and the summary prints the seed.

*Alternative:* one global RNG. Results would change whenever a bin is added or removed, or the query order changes.

### 4. Cycle detection

For each bin with planned dates:
- With one date, the cycle is 28 days.
- Otherwise, try P ∈ (1, 7, 14, 21, 28) in order. Take the residues `date.toordinal() % P` of the stored dates. P fits when every day of the calendar months covered by the stored dates whose residue is in that set is exactly a stored date.
- If no P fits, use P = 28 with the stored residues.

A day is planned when `day.toordinal() % P` is in the residue set. Treating single dates as 28 days, not "same day of month", keeps the rule uniform and avoids 21-day false fits (a single date between Oct 11 and 21 fits P = 21 by accident).

### 5. Holidays from the `holidays` package

Use `holidays.country_holidays("LT", years=range(sim_start.year, end.year + 1))`, precomputed into a `set[date]`. It covers Easter Sunday and Monday, Mother's and Father's Day, and Dec 24. *Alternative:* a hand-written table. It needs an Easter calculation and yearly upkeep. One small pure-Python dependency is cheaper and more reliable.

### 6. Schema: four new columns in migration `0011`

`bin_days` gets the following columns:
- `collection_status TEXT NOT NULL` with `CHECK (collection_status IN ('none','collected','retry_collected','failed','missed'))`.
- `holidays_since_last_collection SMALLINT NOT NULL CHECK (>= 0)`.
- `collections_last_28d SMALLINT NOT NULL CHECK (BETWEEN 0 AND 28)`.
- `missed_collections_28d SMALLINT NOT NULL CHECK (BETWEEN 0 AND 28)`.

The migration first truncates `bin_days`. The table is derived and must be rebuilt anyway, and NOT NULL columns cannot be added to existing rows without defaults. TEXT with a CHECK constraint, not a Postgres ENUM, matches the existing style (`ck_vasa_import_runs_phase`) and stays readable in CSV exports.

### 7. Argument validation before connecting

`--seed` (int), `--p-first`, `--p-retry1` and `--p-retry2` (floats in [0, 1]), and `--holiday-factor` (float ≥ 0) are validated in argparse, together with the existing date and range checks. Invalid values exit with 1 before the engine is created.

## Shared contract changes

`bin_days` is the input contract for the fill-level generator and ML features. The changes are additive, plus a narrower set of bins, since bins without a schedule now drop out. The generator should:
- reset fill on `collected` and `retry_collected`, and
- treat the four columns as **synthetic**.

The README table and the verification doc are updated in the same change.

## Risks / Trade-offs

- [The one-month snapshot may not represent the whole year, for example seasonal schedules.] → The assumption is stated in the spec and README. A rebuild after a newer schedule sync uses the newer cycle.
- [The failure probabilities are assumptions.] → They are CLI flags, printed in the summary, and documented with the `bin_hist` reference rates.
- [Longer rebuilds (minutes for five years).] → It's an offline, explicit command. The simulation streams into the temporary table first, and `TRUNCATE`'s exclusive lock is taken only for the final `INSERT ... SELECT`.
- [The warm-up starts with no "last collection" state.] → 35 days covers the 28-day windows and one full cycle for every cycle length. Edge cases fall back to "count from the simulation start", as the spec defines.
- [A single schedule fetch failure leaves a bin with an old month's dates.] → Cycle detection works on any month's dates. Only the stored dates matter.
- [Changing `--start` shifts the warm-up and therefore the random draws.] → Reproducibility is defined for identical arguments, which the spec states.

## Migration Plan

1. `alembic upgrade head` applies `0011`, which empties `bin_days` and adds the columns.
2. `uv sync` installs `holidays`, and the Docker image is rebuilt.
3. Rerun `python -m app.interfaces.bin_days --start ... --end ...`.

Rollback: `alembic downgrade 0010` drops the columns, which leaves stale-but-valid rows. Then rebuild with the previous code.
