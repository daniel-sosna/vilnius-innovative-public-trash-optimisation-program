# Bin population verification

Repeatable manual checks for `python -m app.interfaces.bin_population`. Run them against a
**disposable or local** database: a rebuild replaces `population_cells` and `bin_population`,
and check 6 temporarily deletes one allocation. Prerequisites: `docker compose up -d`,
migrations applied, the three exports imported and `backend/data/population_density_1ha.geojson`
in place. Expected numbers are for the current files (21,951 bins).

```bash
POP="docker compose exec -T backend uv run python -m app.interfaces.bin_population"
SQL() { docker compose exec -T db psql -U viptop -d viptop -Atc "$1"; }
```

## 1. Rebuild and summary

```bash
$POP; echo "exit=$?"
```

Expected: exit 0; `14079 polygons (7508 suppressed, 100 null), 544476 estimated residents`;
`21951 bins, 21951 with a polygon, 0 without`; and one line per waste type (mixed, paper/plastic,
glass) with unallocated residents 0.

## 2. Row counts

```bash
SQL "select (select count(*) from population_cells), (select count(*) from bin_population), (select count(*) from bins)"
```

Expected: `14079|21951|21951`.

## 3. Factors add up to the residents

```bash
SQL "select b.waste_type, round(sum(p.resident_factor)::numeric, 3), (select round(sum(residents)::numeric, 3) from population_cells) from bin_population p join bins b on b.id = p.bin_id group by 1 order by 1"
```

Expected: for each of the three waste types the two sums are equal (about 544476).

## 4. Non-residential bins have 0

```bash
SQL "select count(*) from bin_population p join bins b on b.id = p.bin_id where p.resident_factor > 0 and (b.capacity_m3 is null or b.capacity_m3 <= 0 or b.object_group is null or b.object_group not in ('Daugiabučiai namai','Dvibučiai','Daugiabučių/garažų bendrijos','Sodų bendrijos','Sodų/garažų bendrijos'))"
```

Expected: `0`.

## 5. Polygon contains the bin

```bash
SQL "select count(*) from bin_population p join bins b on b.id = p.bin_id join population_cells c on c.id = p.population_cell_id where b.longitude not between c.min_lon and c.max_lon or b.latitude not between c.min_lat and c.max_lat"
SQL "select count(*) filter (where p.population_cell_id is null), count(*) filter (where c.residents = 0) from bin_population p left join population_cells c on c.id = p.population_cell_id"
```

Expected: `0`, then `0|4466` (bins in null-density polygons).

Median of a 1.1 m³ apartment mixed-waste bin:

```bash
SQL "select round(percentile_cont(0.5) within group (order by p.resident_factor)::numeric, 1) from bin_population p join bins b on b.id = p.bin_id where b.object_group = 'Daugiabučiai namai' and b.capacity_m3 = 1.1 and b.waste_type = 'Mixed municipal waste'"
```

Expected: `37.0`.

## 6. `bin_days` precondition

```bash
SQL "delete from bin_population where bin_id = (select min(bin_id) from bin_population)"
docker compose exec -T backend uv run python -m app.interfaces.bin_days --start 2026-09-09 --end 2026-10-09; echo "exit=$?"
$POP
```

Expected: exit 1 with `1 eligible bins have no resident allocation; run python -m app.interfaces.bin_population first` and `bin_days` unchanged. (Right after a CSV import it reports 21,840.) The last command restores the allocation.

## 7. Reproducible

```bash
HASH="select md5(string_agg(t::text, ',' order by bin_id)) from bin_population t"
SQL "$HASH"; $POP > /dev/null; SQL "$HASH"
```

Expected: identical hashes.

## 8. Argument errors, no database needed

```bash
$POP --suppressed-density 11; echo "exit=$?"   # 1, names '11'
$POP --file /nope.geojson; echo "exit=$?"      # 1, names /nope.geojson
```

## 9. CSV import interaction

```bash
mkdir backend/data/histonly && cp backend/data/bin_hist_*.csv backend/data/histonly/
docker compose exec -T backend uv run python -m app.interfaces.table_import --dir /app/data/histonly
rm -r backend/data/histonly
SQL "select count(*) from bin_population"
docker compose exec -T backend uv run python -m app.interfaces.table_import
SQL "select (select count(*) from bin_population), (select count(*) from population_cells)"
```

Expected: `21951` after the history-only import; after the full import `0|14079` and the output
names `python -m app.interfaces.bin_population` as the refill command.
