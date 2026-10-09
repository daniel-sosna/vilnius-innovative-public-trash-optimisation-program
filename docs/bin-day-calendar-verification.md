# Bin-day calendar verification

Repeatable manual checks for `python -m app.interfaces.bin_days`. Run them against a
**disposable or local** database: every rebuild replaces the whole `bin_days` table, and
check 7 temporarily empties `bin_hist`. Prerequisites: `docker compose up -d`, migrations
applied, and the three exports imported (see the README section "Import table CSV exports").
Expected numbers are for the current exports (21,951 bins, 147 without a sub-district).

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
`bin_days rebuilt for 2026-09-09..2026-10-09 (31 days): 21804 bins included, 147 excluded without sub_district, 675924 rows`.

## 2. One row per eligible bin per day

```bash
SQL "select count(*), count(distinct (bin_id, date)), (select count(*) from bins where sub_district is not null) * 31, min(date), max(date) from bin_days"
```

Expected: `675924|675924|675924|2026-09-09|2026-10-09`.

## 3. Eligibility

```bash
SQL "select count(*) from bin_days d join bins b on b.id = d.bin_id where b.sub_district is null"
SQL "select count(distinct bin_id), count(*) from bin_days where object_group is null"
```

Expected: `0`, then `476|14756` (476 bins without an object group, 31 rows each).

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

## 6. Bin deletion cascades

```bash
SQLF <<'EOF'
begin;
delete from bins where id = 3;
select (select count(*) from bin_days where bin_id = 3), (select count(*) from bin_days);
rollback;
EOF
```

Expected: `0|675893` (bin 3's 31 rows removed, all others kept); the rollback restores it.

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

## 8. Single days, seasons and ISO weeks

```bash
$BIN_DAYS --start 2026-12-01 --end 2026-12-01
SQL "select count(*), string_agg(distinct concat_ws('|', month, season), ',') from bin_days"
$BIN_DAYS --start 2027-01-01 --end 2027-01-01
SQL "select count(*), string_agg(distinct concat_ws('|', day_of_week, week_of_year), ',') from bin_days"
```

Expected: `21804|12|1` (December is winter), then `21804|5|53` (Friday in ISO week 53).

## 9. Narrower range replaces wider one

```bash
$BIN_DAYS --start 2026-09-01 --end 2026-10-31
SQL "select min(date), max(date), count(*) from bin_days"
$BIN_DAYS --start 2026-09-09 --end 2026-10-09
SQL "select min(date), max(date), count(*) from bin_days"
```

Expected: `2026-09-01|2026-10-31|1330044`, then `2026-09-09|2026-10-09|675924`.

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
both counts are `675924`.

## 11. Argument errors

```bash
$BIN_DAYS --start 2026-09-09; echo "exit=$?"                          # 1, --end is required
$BIN_DAYS --start 2026-13-01 --end 2026-10-09; echo "exit=$?"         # 1, names '2026-13-01'
$BIN_DAYS --start 2026-10-09 --end 2026-09-09; echo "exit=$?"         # 1, range is reversed
$BIN_DAYS --start 2026-09-09 --end 2031-09-10; echo "exit=$?"         # 1, 1828 days, at most 1827
$BIN_DAYS --help > /dev/null; echo "exit=$?"                          # 0
SQL "select count(*) from bin_days"                                   # unchanged: 675924
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
