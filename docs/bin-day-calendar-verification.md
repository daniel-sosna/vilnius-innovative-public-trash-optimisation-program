# Bin-day calendar verification

Repeatable manual checks for `python -m app.interfaces.bin_days`. Run them against a
**disposable or local** database: every rebuild replaces the whole `bin_days` table, and
check 7 temporarily empties `bin_hist`. Prerequisites: `docker compose up -d`, migrations
applied, and the three exports imported (see the README section "Import table CSV exports").
Expected numbers are for the current exports (21,951 bins, 147 without a sub-district, 109 further without a schedule).

Shorthand used below:

```bash
BIN_DAYS="docker compose exec -T backend uv run python -m app.interfaces.bin_days"
SQL() { docker compose exec -T db psql -U viptop -d viptop -Atc "$1"; }
SQLF() { docker compose exec -T db psql -U viptop -d viptop -At -v ON_ERROR_STOP=1; }  # reads stdin
```

Native alternative: run `uv run python -m app.interfaces.bin_days` from `backend/` and use
`psql` with your own connection.

## 1. Rebuild and summary

```bash
$BIN_DAYS --start 2026-09-09 --end 2026-10-09; echo "exit=$?"
```

Expected: exit 0 and
`bin_days rebuilt for 2026-09-09..2026-10-09 (31 days): 21695 bins included, 147 excluded without sub_district, 109 excluded without schedule, 672545 rows`.

## 2. One row per eligible bin per day

```bash
SQL "select count(*), count(distinct (bin_id, date)), (select count(distinct b.id) from bins b join bin_schedule s on s.bin_id = b.id where b.sub_district is not null) * 31, min(date), max(date) from bin_days"
```

Expected: `672545|672545|672545|2026-09-09|2026-10-09`.

## 3. Eligibility

```bash
SQL "select count(*) from bin_days d join bins b on b.id = d.bin_id where b.sub_district is null"
SQL "select count(distinct bin_id), count(*) from bin_days where object_group is null"
```

Expected: `0`, then the number of eligible bins without an object group and 31 times that (compare with `select count(distinct b.id) from bins b join bin_schedule s on s.bin_id = b.id where b.sub_district is not null and b.object_group is null`).

## 4. Calendar features

```bash
SQL "select distinct day_of_week, week_of_year, month, season from bin_days where date = '2026-10-09'"
SQL "select date, day_of_week, week_of_year, month, season from bin_days group by 1, 2, 3, 4, 5 order by 1" > /tmp/bin_days_calendar.txt
python3 -c "
import datetime as d
rows = [l.split('|') for l in open('/tmp/bin_days_calendar.txt').read().split()]
bad = [r for r in rows if (lambda x: [str(x.isoweekday()), str(x.isocalendar().week), str(x.month), str(x.month % 12 // 3 + 1)])(d.date.fromisoformat(r[0])) != r[1:]]
print(len(rows), 'dates,', len(bad), 'mismatches')"
```

Expected: `5|41|10|4`, then `31 dates, 0 mismatches`. Each date has exactly one feature
combination, and it matches Python's ISO calendar.

## 5. Bin attributes copied

```bash
SQL "select count(*) from bin_days d join bins b on b.id = d.bin_id where (d.site_id, d.waste_type, d.capacity_m3, d.sub_district, d.object_group) is distinct from (b.site_id, b.waste_type, b.capacity_m3, b.sub_district, b.object_group)"
SQL "select distinct site_id, waste_type, capacity_m3, sub_district, object_group from bin_days where bin_id = 3"
```

Expected: `0`, then `2|Mixed municipal waste|1.1|Panerių sen.|Komercinė paskirtis`.

Population attributes (run `python -m app.interfaces.bin_population` first):

```bash
SQL "select count(*) from bin_days d join bin_population p on p.bin_id = d.bin_id where (d.population_cell_id, d.resident_factor) is distinct from (p.population_cell_id, p.resident_factor)"
```

Expected: `0`.

## 6. Bin deletion cascades

```bash
SQLF <<'EOF'
begin;
delete from bins where id = 3;
select (select count(*) from bin_days where bin_id = 3), (select count(*) from bin_days);
rollback;
EOF
```

Expected: `0|672514` (bin 3's 31 rows removed, all others kept); the rollback restores it.

## 7. Independent of service history

```bash
HASH="select md5(string_agg(t::text, ',' order by bin_id, date)) from bin_days t"
SQL "$HASH"
SQL "delete from bin_hist"
$BIN_DAYS --start 2026-09-09 --end 2026-10-09
SQL "$HASH"
mkdir backend/data/histonly && cp backend/data/bin_hist_*.csv backend/data/histonly/
docker compose exec -T backend uv run python -m app.interfaces.table_import --dir /app/data/histonly
rm -r backend/data/histonly
```

Expected: both hashes are identical. The history-only import restores `bin_hist` without
touching `bin_days`.

## 7b. Reproducible, seed-dependent

```bash
$BIN_DAYS --start 2026-09-09 --end 2026-10-09 --seed 7 && SQL "$HASH"
$BIN_DAYS --start 2026-09-09 --end 2026-10-09 --seed 7 && SQL "$HASH"
$BIN_DAYS --start 2026-09-09 --end 2026-10-09 --seed 8 && SQL "$HASH"
```

Expected: the first two hashes are identical and the third differs. (Run check 7's `HASH`
definition first.)

## 7c. Collection status

```bash
$BIN_DAYS --start 2026-09-09 --end 2026-10-09
SQL "select collection_status, count(*) from bin_days group by 1 order by 1"
# retry_collected needs a failed day before it; a failed day is followed by retry or missed
SQL "select count(*) from (select date, collection_status s, lag(collection_status) over (partition by bin_id order by date) p from bin_days) t where s = 'retry_collected' and p is distinct from 'failed' and date > '2026-09-09'"
SQL "select count(*) from (select collection_status s, lag(collection_status) over w p1, lag(collection_status, 2) over w p2 from bin_days window w as (partition by bin_id order by date)) t where s = 'failed' and p1 = 'failed' and p2 = 'failed'"
```

Expected: only the five statuses, `collected` and `none` dominate, then `0` and `0`
(no `retry_collected` without a preceding `failed`, never three consecutive `failed`).

## 7d. Look-back features

```bash
SQL "select count(*) from (select collections_last_28d c, missed_collections_28d m,
  count(*) filter (where collection_status in ('collected','retry_collected')) over w rc,
  count(*) filter (where collection_status = 'missed') over w rm, date
  from bin_days window w as (partition by bin_id order by date rows between 28 preceding and 1 preceding)) t
  where date >= '2026-10-07' and (c <> rc or m <> rm)"
```

Expected: `0`. The SQL window only sees rows from `--start`, so the comparison starts 28 days
after it (2026-10-07). Earlier rows get their history from the 35-day warm-up instead.

Holiday counts (2026-11-01 and 2026-11-02 are holidays):

```bash
$BIN_DAYS --start 2026-10-25 --end 2026-11-05 --p-first 0
SQL "select date, max(holidays_since_last_collection) from bin_days where date in ('2026-11-03','2026-11-04') group by 1 order by 1"
```

Expected: `2026-11-03|2` and `2026-11-04|2` (bins last collected on or before 2026-10-31).

## 7e. No failures with `--p-first 0`

```bash
$BIN_DAYS --start 2026-09-09 --end 2026-10-09 --p-first 0
SQL "select count(*) from bin_days where collection_status in ('failed','missed','retry_collected')"
```

Expected: `0`.

## 8. Single days, seasons and ISO weeks

```bash
$BIN_DAYS --start 2026-12-01 --end 2026-12-01
SQL "select count(*), string_agg(distinct concat_ws('|', month, season), ',') from bin_days"
$BIN_DAYS --start 2027-01-01 --end 2027-01-01
SQL "select count(*), string_agg(distinct concat_ws('|', day_of_week, week_of_year), ',') from bin_days"
```

Expected: `21695|12|1` (December is winter), then `21695|5|53` (Friday in ISO week 53).

## 9. Narrower range replaces wider one

```bash
$BIN_DAYS --start 2026-09-01 --end 2026-10-31
SQL "select min(date), max(date), count(*) from bin_days"
$BIN_DAYS --start 2026-09-09 --end 2026-10-09
SQL "select min(date), max(date), count(*) from bin_days"
```

Expected: `2026-09-01|2026-10-31|1323365`, then `2026-09-09|2026-10-09|672545`.

## 10. Failure keeps previous contents

Hold a lock on the table for 20 seconds so the rebuild runs into its 5-second lock timeout.

```bash
SQL "select count(*) from bin_days"
docker compose exec -T db psql -U viptop -d viptop -c "begin; lock table bin_days in access share mode; select pg_sleep(20); commit" > /dev/null &
sleep 2
$BIN_DAYS --start 2026-12-01 --end 2026-12-01; echo "exit=$?"
wait
SQL "select count(*) from bin_days"
```

Expected: exit 1 with `Bin-day rebuild failed, nothing was changed: LockNotAvailable: ...`;
both counts are `672545`.

## 11. Argument errors

```bash
$BIN_DAYS --start 2026-09-09; echo "exit=$?"                          # 1, --end is required
$BIN_DAYS --start 2026-13-01 --end 2026-10-09; echo "exit=$?"         # 1, names '2026-13-01'
$BIN_DAYS --start 2026-10-09 --end 2026-09-09; echo "exit=$?"         # 1, range is reversed
$BIN_DAYS --start 2026-09-09 --end 2031-09-10; echo "exit=$?"         # 1, 1828 days, at most 1827
$BIN_DAYS --start 2026-09-09 --end 2026-10-09 --p-first 1.5; echo "exit=$?"      # 1, names 1.5
$BIN_DAYS --start 2026-09-09 --end 2026-10-09 --holiday-factor -1; echo "exit=$?" # 1, names -1
$BIN_DAYS --help > /dev/null; echo "exit=$?"                          # 0
SQL "select count(*) from bin_days"                                   # unchanged: 672545
```

A full five-year range (`--start 2027-03-01 --end 2032-02-29`, 1,827 days) is accepted, but
it writes about 40M rows. To check only that it passes validation, point it at an unreachable
database:

```bash
docker compose exec -T -e DATABASE_URL=postgresql+psycopg://viptop:secret@nohost/viptop backend \
  uv run python -m app.interfaces.bin_days --start 2027-03-01 --end 2032-02-29; echo "exit=$?"
```

Expected: exit 1 with `nothing was changed: OperationalError: failed to resolve host 'nohost' ...`.
The message passes validation and never contains the password.
