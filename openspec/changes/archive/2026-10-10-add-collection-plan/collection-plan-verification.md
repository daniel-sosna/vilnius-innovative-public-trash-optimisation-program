# Collection plan verification

Repeatable manual checks for `python -m app.interfaces.collection_plan` and `get_plan`. Run them
against a **disposable or local** database: check 5 imports the CSV exports, which replaces
`sites`, `bins` and `bin_hist`. Prerequisites: `docker compose up -d`, migrations applied, and
the three exports imported (see the README section "Import table CSV exports"). Expected
numbers are for the current exports (21,951 bins; the mock draws, so counts depend on them).

Shorthand used below:

```bash
PLAN="docker compose exec -T backend uv run python -m app.interfaces.collection_plan"
SQL() { docker compose exec -T db psql -U viptop -d viptop -Atc "$1"; }
PY() { docker compose exec -T -e PYTHONPATH=/app backend uv run python -c "$1"; }
```

## 1. Rebuild, summary and reproducibility

```bash
$PLAN --date 2026-10-10; echo "exit=$?"
SQL "select count(*), sum(overall_volume_m3), sum(overall_predicted_fill_m3) from collection_stops where date = '2026-10-10'"
$PLAN --date 2026-10-10; SQL "select count(*), sum(overall_volume_m3), sum(overall_predicted_fill_m3) from collection_stops where date = '2026-10-10'"
```

Expected: exit 0, a summary labelled `prediction=MOCK` with the bins evaluated (21951 for the full
exports), the due bins and the stops per carrier; both runs store the same count and totals.

## 2. Integrity, totals and other dates untouched

```bash
$PLAN --date 2026-10-09
# every due bin is in exactly one stop; no bin is in two stops
SQL "select count(*) from (select sb.bin_id from stop_bins sb join collection_stops c on c.id = sb.stop_id where c.date = '2026-10-10' group by 1 having count(*) > 1) x"
# the due flag matches the default threshold 2
SQL "select count(*) from stop_bins sb join collection_stops c on c.id = sb.stop_id where c.date = '2026-10-10' and sb.due <> (sb.predicted_fill > 2)"
# every stop has a due bin and lists exactly its carrier's bins at the site
SQL "select count(*) from collection_stops c where c.date = '2026-10-10' and (not exists (select 1 from stop_bins sb where sb.stop_id = c.id and sb.due) or (select count(*) from stop_bins sb where sb.stop_id = c.id) <> (select count(*) from bins b where b.site_id = c.site_id and b.waste_carrier is not distinct from c.waste_carrier))"
# overall_volume_m3 is the sum of all those bins' capacities
SQL "select count(*) from collection_stops c where c.date = '2026-10-10' and c.overall_volume_m3 <> (select coalesce(sum(coalesce(b.capacity_m3, 0)), 0) from stop_bins sb join bins b on b.id = sb.bin_id where sb.stop_id = c.id)"
# overall_predicted_fill_m3 is capacity times share (0.2, 0.5, 0.8, 1.0, 1.5)
SQL "select count(*) from collection_stops c where c.date = '2026-10-10' and c.overall_predicted_fill_m3 <> (select coalesce(sum(coalesce(b.capacity_m3, 0) * (array[0.2, 0.5, 0.8, 1.0, 1.5])[sb.predicted_fill + 1]), 0) from stop_bins sb join bins b on b.id = sb.bin_id where sb.stop_id = c.id)"
before=$(SQL "select count(*) from collection_stops where date = '2026-10-09'")
$PLAN --date 2026-10-10 --threshold 3; echo "$before / $(SQL "select count(*) from collection_stops where date = '2026-10-09'")"
SQL "select min(sb.predicted_fill) from stop_bins sb join collection_stops c on c.id = sb.stop_id where c.date = '2026-10-10' and sb.due"
```

Expected: `0` for each of the five count queries (the example is 0.6 m3 at level 2 = 0.48 m3, which
the last query checks for every stop); the 2026-10-09 count is identical before and after; after
the rerun with threshold 3 the minimum fill level of a due bin of 2026-10-10 is `4`.

## 3. Reading the plan

```bash
PY "
from datetime import date
from sqlalchemy.orm import Session
from app.core.config import Settings
from app.infrastructure.database import create_database_engine
from app.services.collection_plan import get_plan
with Session(create_database_engine(Settings())) as s:
    d = date(2026, 10, 10)
    print({k: len(v) for k, v in get_plan(s, d).items()})
    print({k: len(v) for k, v in get_plan(s, d, ['Ecoservice', 'Nope', None]).items()})
    print(get_plan(s, date(2030, 1, 1)), get_plan(s, date(2030, 1, 1), ['Ecoservice']))
"
```

Expected: the first line has one entry per carrier with stops (each stop dict has `overall_volume_m3`, `overall_predicted_fill_m3` and bins with a `due` flag) (the exports have no unassigned
bins); the second has exactly `Ecoservice`, `Nope` (0) and `None` (0); the last prints
`{} {'Ecoservice': []}`.

## 4. Invalid input and empty bins

```bash
$PLAN --threshold 5; echo "exit=$?"
$PLAN --date 2026-13-01; echo "exit=$?"
```

Expected: exit 1 each, with an argument error; the stored plan is unchanged. With an empty
`bins` table (for example `TRUNCATE bins CASCADE` on a disposable database, then re-import) the
command logs `no bins are stored` and exits 1.

## 5. CSV import

```bash
docker compose exec -T backend uv run python -m app.interfaces.table_import
SQL "select (select count(*) from collection_stops) || ' ' || (select count(*) from stop_bins)"
```

Expected: the output says `collection_stops emptied with the replaced bins; refill it with python -m app.interfaces.collection_plan` (same for `stop_bins`) and the count is `0 0`. An import with only a `bin_hist_<digits>.csv` (use `--dir` with a folder holding just that file) leaves a stored plan unchanged.
