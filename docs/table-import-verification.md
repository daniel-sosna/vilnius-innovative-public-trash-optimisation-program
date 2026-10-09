# Table CSV import verification

Repeatable manual checks for `python -m app.interfaces.table_import`. Run them against a
**disposable or local** database: every import discards the current contents of the imported
tables. Prerequisites: `docker compose up -d`, migrations applied, and the three exports
(`sites_*.csv`, `bins_*.csv`, `bin_hist_*.csv`) in `backend/data/`. Checks 7, 8, 10 and 12 create
subfolders there (visible in the container as `/app/data/...`); delete them afterwards.

Shorthand used below:

```bash
IMPORT="docker compose exec -T backend uv run python -m app.interfaces.table_import"
SQL() { docker compose exec -T db psql -U viptop -d viptop -Atc "$1"; }
```

Native alternative: run `uv run python -m app.interfaces.table_import` from `backend/` and use
`psql` with your own connection.

## 1. Full import and counts

```bash
$IMPORT; echo "exit=$?"
SQL "select (select count(*) from sites),(select count(*) from bins),(select count(*) from bin_hist)"
```

Expected: exit 0; one `<table> <- <file>: N rows` line per table (about 9.4k sites, 22k bins,
200k history rows); the SQL counts equal the logged counts and `wc -l` of each file minus the
header (history has multi-line values, so compare with `SELECT count` of the file's `id`s
instead if they differ).

## 2. Trucks unchanged

```bash
SQL "select count(*), max(id) from trucks"   # before
$IMPORT
SQL "select count(*), max(id) from trucks"   # after
```

Expected: identical output.

## 3. IDs preserved

```bash
SQL "select site_id from bins where id = 3"
```

Expected: `2` (as in `bins_*.csv`).

## 4. NULL versus empty reason

```bash
SQL "select count(*) filter (where non_serviced_reason is null), count(*) filter (where non_serviced_reason = '') from bin_hist"
python3 -c "import csv,glob;r=list(csv.reader(open(glob.glob('backend/data/bin_hist_*.csv')[0],newline='')))[1:];print(sum(x[4]=='NULL' for x in r),sum(x[4]=='' for x in r))"  # NULL vs empty from the file
```

Expected: the SQL counts equal the Python counts (current export: `5658|188657`).

## 5. Identity sequences advanced

```bash
SQL "select nextval(pg_get_serial_sequence('bins','id')) > (select max(id) from bins)"
SQL "select nextval(pg_get_serial_sequence('bin_hist','id')) > (select max(id) from bin_hist)"
```

Expected: `t` for both (this consumes one sequence value each).

## 6. Sync state cleared

Run `docker compose exec backend uv run python -m app.interfaces.bin_sync --max-sites 1`
beforehand so a run exists, then import.

```bash
SQL "select (select count(*) from vasa_import_runs),(select count(*) from vasa_import_progress)"
```

Expected: `0|0`.

## 7. Rollback on a corrupted file

```bash
mkdir backend/data/bad && cp backend/data/*.csv backend/data/bad/
echo '99999999,999999999,not-a-date,true,"",NULL' >> backend/data/bad/bin_hist_*.csv
SQL "select (select count(*) from sites),(select count(*) from bins),(select count(*) from bin_hist)"
$IMPORT --dir /app/data/bad; echo "exit=$?"
SQL "select (select count(*) from sites),(select count(*) from bins),(select count(*) from bin_hist)"
```

Expected: exit 1 with a readable `Table import failed, nothing was changed: ...` line without
credentials; both count lines identical.

## 8. Newest file wins

```bash
mkdir backend/data/two && cp backend/data/*.csv backend/data/two/
head -1 backend/data/bins_*.csv > backend/data/two/bins_202001010000.csv   # older, header only
$IMPORT --dir /app/data/two
```

Expected: `bins` is loaded from the newer file (same count as check 1); the older file is not used.

## 9. Idempotent rerun

```bash
$IMPORT; SQL "select count(*) from bins"; $IMPORT; SQL "select count(*) from bins"
```

Expected: both runs exit 0 with identical counts.

## 10. Error cases

```bash
$IMPORT --dir /nonexistent; echo "exit=$?"        # 1, reports the path
mkdir backend/data/empty
$IMPORT --dir /app/data/empty; echo "exit=$?"                # 1, nothing to import
mkdir backend/data/sites && cp backend/data/sites_*.csv backend/data/sites/
$IMPORT --dir /app/data/sites; echo "exit=$?"          # 1, hint about referencing tables
SQL "select (select count(*) from sites),(select count(*) from bins),(select count(*) from bin_hist)"  # unchanged
```

## 11. Sync after import

```bash
docker compose exec backend uv run python -m app.interfaces.bin_sync --max-sites 10
SQL "select max(id) from bins"; SQL "select max(id) from bin_hist"
```

Expected: starts a new pass without key conflicts; any new `bins`/`bin_hist` IDs are greater
than the imported maxima.

## 12. Bin-day calendar emptied only with bins

Seed a few calendar rows, then import everything, then only history.

```bash
SEED="insert into bin_days select id, date '2026-10-09', 5, 41, 10, 4, site_id, waste_type, capacity_m3, sub_district, object_group from bins where sub_district is not null limit 3"
SQL "$SEED"
$IMPORT; echo "exit=$?"
SQL "select count(*) from bin_days"                      # 0
SQL "$SEED"
mkdir backend/data/histonly && cp backend/data/bin_hist_*.csv backend/data/histonly/
$IMPORT --dir /app/data/histonly; echo "exit=$?"
SQL "select count(*) from bin_days"                      # 3
```

Expected: both imports exit 0. The full import logs `bin_days emptied with the replaced bins`
and leaves `0` rows; the history-only import keeps the `3` rows and does not log the line.
Afterwards delete `backend/data/histonly` and rebuild the calendar (see the README section
"Bin-day calendar").
