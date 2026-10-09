# Design

## Context

- Bins live in `bins` (migration `0004`). `bin_id` and `site_id` are `BIGINT`, `capacity_m3` is `NUMERIC`, and `sub_district` and `object_group` are nullable text.
- The current data has 21,951 bins: 147 have no `sub_district` and 476 have no `object_group`.
- Development data comes from `python -m app.interfaces.table_import`. In one transaction it `TRUNCATE`s every table that has a file. It deliberately fails with `FeatureNotSupported` when a table being replaced is still referenced by a table without a file. Any table in `Base.metadata` takes part in file discovery.
- VASA sync cleanup removes bins with a row-level `DELETE` (`services/bin_sync.py`), so `ON DELETE CASCADE` applies there. `TRUNCATE` does not fire cascades.
- CLIs live under `app/interfaces/<name>/` and run as `python -m`. They use `Settings()` and `create_database_engine` and return exit codes 0 and 1 with credential-free messages.

## Goals / Non-Goals

**Goals:**
- One SQL statement builds the whole grid inside PostgreSQL, so a 31-day rebuild takes seconds.
- The table stays consistent with `bins` in both deletion paths: sync cleanup and CSV import.

**Non-Goals:**
- Incremental or append-only rebuilds. Every rebuild is a full replacement.
- Reading the table through the HTTP API or the frontend.
- Historical bin attributes, and bin lifetime (install and removal dates).

## Decisions

### D1. A real table with a foreign key to `bins` and `ON DELETE CASCADE`

```
bin_days
  bin_id        BIGINT    NOT NULL  FK -> bins.id ON DELETE CASCADE
  date          DATE      NOT NULL
  day_of_week   SMALLINT  NOT NULL  CHECK 1..7
  week_of_year  SMALLINT  NOT NULL  CHECK 1..53
  month         SMALLINT  NOT NULL  CHECK 1..12
  season        SMALLINT  NOT NULL  CHECK 1..4
  site_id       BIGINT    NOT NULL
  waste_type    TEXT      NOT NULL
  capacity_m3   NUMERIC
  sub_district  TEXT      NOT NULL
  object_group  TEXT
  PRIMARY KEY (bin_id, date)
```

- **Primary key.** `(bin_id, date)` enforces the one-row-per-bin-per-day rule. It also serves the generator's per-bin time-series reads without a surrogate `id`.
- **Foreign key.** Without one, sync cleanup would leave orphan rows that look valid.
- **`site_id`.** It is a denormalised copy with no foreign key. Sites can only disappear after their bins do, and the bin cascade already covers that.
- **Constraints.** The CHECK constraints follow the project's existing style and catch feature-calculation bugs at insert time.
- **Alternative rejected:** a SQL view, which would recompute the grid on every read. The team chose a stored table.

### D2. Compute everything in one `INSERT ... SELECT`

```sql
TRUNCATE bin_days;
INSERT INTO bin_days (...)
SELECT b.id, d::date,
       EXTRACT(ISODOW FROM d), EXTRACT(WEEK FROM d), EXTRACT(MONTH FROM d),
       EXTRACT(MONTH FROM d)::int % 12 / 3 + 1,          -- Dec,Jan,Feb=1 ... Sep,Oct,Nov=4
       b.site_id, b.waste_type, b.capacity_m3, b.sub_district, b.object_group
FROM generate_series(:start, :end, interval '1 day') AS d
CROSS JOIN bins b
WHERE b.sub_district IS NOT NULL;
```

- PostgreSQL's `WEEK` and `ISODOW` follow ISO 8601, which matches the spec.
- Both statements run in one `engine.begin()` transaction with the same `SET LOCAL lock_timeout` as the importer. A failure rolls back to the previous contents.
- Summary counts come from the same transaction after the insert:
  - included bins: `count(DISTINCT bin_id)`
  - excluded bins: `count(*) FROM bins WHERE sub_district IS NULL`
  - total rows
- **Alternative rejected:** building the grid in Python or pandas. It would add a dependency and push about 676k rows over the wire for no gain.

### D3. The CSV import empties `bin_days` when it replaces `bins`

In `table_import/cli.py`, `load_tables` adds `bin_days` to the `TRUNCATE` list when `bins` is selected and `bin_days` is not. This mirrors how the sync state tables are added today. The two tables go in one statement, `TRUNCATE bins, ..., bin_days`, so PostgreSQL accepts the foreign key.

- **Why:** without this, adding the foreign key would make the standard collection import fail with "referencing tables also need files", which would break the development workflow.
- **Alternative rejected:** no foreign key on `bin_days`. The import would keep working, but the table would silently hold rows for bins that no longer exist or have changed. That puts correctness at risk for data the generator trusts.
- **Side effect:** `bin_days` becomes a schema table, so a `bin_days_<digits>.csv` would be imported like any other table. This is harmless and consistent with the importer.

### D4. CLI shape

- Package `app/interfaces/bin_days/`, with `__init__.py`, `__main__.py` and `cli.py`, in the same layout as `table_import`.
- Usage: `python -m app.interfaces.bin_days --start YYYY-MM-DD --end YYYY-MM-DD`.
- argparse validates the dates with `date.fromisoformat`. As in `table_import`, argparse's exit code 2 is mapped to 1, and `--help` returns 0.
- A reversed range, or a range longer than 1,827 days (both ends included), is rejected before the database is opened.
- 1,827 days is the longest span five calendar years can cover: 5 × 365 days plus two leap days (e.g. 2027-03-01..2032-02-29). A day count is simpler and more precise than "same date plus five years", which is undefined when the start is Feb 29.
- There are no default dates: the operator states the range explicitly, which keeps rebuilds reproducible.
- The table is created by migration `0005_bin_days.py` (explicit SQL, like `0004`). Its `downgrade` drops the table.
- The ORM model `BinDay` goes in `infrastructure/models.py` so that table discovery and the metadata stay complete.

## Risks / Trade-offs

- **Calendar empty after a collection import.** Developers must remember to rebuild. → The README import section and the import's log line say so. The rebuild is one fast command.
- **Huge range by typo** (e.g. `--end 2062-10-09`, about 300M rows). → The 1,827-day limit rejects it before the database is opened. The largest allowed rebuild is about 40M rows (21.8k bins × 1,827 days). That is slow but finite, and the summary prints the day count.
- **Attribute snapshot.** Past dates show today's capacity and grouping. → This is documented in the spec as an assumption. No historical attributes exist in the source.
- **ISO week-year mismatch near New Year.** 2027-01-01 is in week 53. → This is documented, and no ISO year column is added. The current data range does not cross a year boundary.
- **`TRUNCATE` takes an `ACCESS EXCLUSIVE` lock.** Concurrent readers wait during a rebuild of a few seconds. → The rebuild is manual, and `lock_timeout` fails fast if another session holds the table.

**Shared contract:** the `bin_days` column set and its meanings are the interface to the future synthetic fill-level generator (data/ML). Renaming or redefining columns requires coordinating with that component. Retry handling and outcomes are the generator's job: it reads `bin_hist` directly, and if one bin has several events on the same day, it uses the last one.

## Migration Plan

1. Deploy: the backend entrypoint runs `alembic upgrade head`, which creates an empty `bin_days`.
2. If the collection data is not loaded yet, run `table_import`.
3. Run `python -m app.interfaces.bin_days --start 2026-09-09 --end 2026-10-09`.

Rollback: `alembic downgrade 0004` drops the table. No other table is affected.
