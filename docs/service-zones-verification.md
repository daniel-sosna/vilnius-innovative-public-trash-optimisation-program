# Service-zone verification

Use a disposable verification database for replacement, malformed-input and
rollback checks. Set `DATABASE_URL` to that database before the commands below;
do not run failure fixtures against shared developer data. Native commands run
from `backend/`; the Docker equivalent prepends `docker compose exec backend uv run`.

## Source and migration

Run `uv run alembic upgrade head`. Revision `0015` creates an empty `service_zones`
table with `id`, `zone_name`, `zone_number` and JSONB `geometry`. It performs no
import. On an isolated database at `0015`, downgrade to `0014`, verify only the
zone table was removed, then upgrade again. At the merged head (`0016`), first
downgrade to `0015` to remove district boundaries before checking zone rollback.
Other table contents must remain unchanged.

The supplied source is `backend/data/serv_zones.geojson`. Retain it and copy it as
`service_zones.geojson` into the configured data directory; for a shared Docker
mount use the host path named by `VIPTOP_DATA_DIR`. Verify the copies have equal
SHA-256 digests. There are five CRS84 Polygons:

| Name | Zone number |
| --- | --- |
| Šiaurinė | 1 |
| Rytinė | 2 |
| Pietinė | 3 |
| Vakarinė | 4 |
| Centrinė | 5 |

The input count is a fixture expectation, not a parser restriction. Source
descriptions and `OBJECTID` are not persisted. Data files remain external and
Git-ignored; executable import code is under `app/interfaces/service_zones/`.

## Dedicated import

```bash
uv run python -m app.interfaces.service_zones
uv run python -m app.interfaces.service_zones
```

Both runs must report five rows and exit 0. Check the resulting records:

```sql
SELECT zone_name, zone_number, geometry->>'type' AS geometry_type
FROM service_zones ORDER BY zone_number;
SELECT count(*), count(DISTINCT zone_number) FROM service_zones;
```

Counts must both be 5 and names/numbers must match the table above. Run with
`--file /path/to/another.geojson` to exercise explicit file selection. Run with
an absent file and verify exit 1 with the previous records unchanged.

For structural validation without any database writes, run this from `backend/`:

```bash
uv run python - <<'PY'
from app.core.config import data_dir
from app.interfaces.service_zones.importer import parse_zones
zones = parse_zones(data_dir() / 'service_zones.geojson')
assert len(zones) == 5
assert [(z['zone_name'], z['zone_number']) for z in zones] == [
    ('Šiaurinė', 1), ('Rytinė', 2), ('Pietinė', 3), ('Vakarinė', 4), ('Centrinė', 5)]
assert all(z['geometry']['type'] == 'Polygon' for z in zones)
print('PASS: five named zones, integer numbers and Polygon geometry')
PY
```

Copy the input to a temporary directory to exercise malformed JSON, missing/blank
`ZONA`, non-integer/boolean/duplicate `ZONOS_NR`, wrong geometry type, open or short
rings, non-finite/out-of-range coordinates and unsupported CRS. Each dedicated
invocation must exit 1 without changing stored rows. A valid Polygon with an
interior ring must retain both rings. A valid reduced source must remove absent
zones; a valid `{"type":"FeatureCollection","features":[]}` must clear zones.
Re-import the supplied source after these isolated checks.

The connection-level `replace_zones(connection, zones)` does not commit. To
exercise database rollback manually, begin a transaction, pass duplicate zone
numbers to the writer, and verify the unique-constraint failure rolls back the
truncate and inserts. Compare every pre-existing zone field, not just its count.

## Regular import and rollback

Before collection-data checks, confirm the selected directory contains
`sites_<digits>.csv`, `bins_<digits>.csv` and `bin_hist_<digits>.csv`. Use
`python -m app.interfaces.table_import`; never obtain development data through
`bin_sync`. Existing bin-population/bin-day refill order still applies.

Run `uv run python -m app.interfaces.table_import` against the isolated database
and configured data directory. The row summary must include CSV-selected tables
and five zones. Then copy only the zone source into a temporary directory and
run `uv run python -m app.interfaces.table_import --dir /path/to/zone-only-dir`:
this must succeed and replace zones without altering collection tables.

For partial imports, create a temporary directory containing only a
`bin_hist_<digits>.csv` export referencing existing bins. The same `--dir`
command must warn about the missing zone file, import the history and preserve
every stored zone. It must not find a zone source in the default/shared directory.
An empty directory must return exit 1 without writes.

For atomicity checks, capture counts and contents of all affected tables
(`sites`, `bins`, `bin_hist`, `bin_schedule`, `bin_population`, `bin_days`,
`resident_requests`, `service_zones`, `vasa_import_runs`, `vasa_import_progress`).
Compare a deterministic content digest as well as counts, for example:

```sql
SELECT count(*), md5(COALESCE(string_agg(md5(row_to_json(r)::text), ''
    ORDER BY md5(row_to_json(r)::text)), '')) FROM service_zones r;
```

Use temporary copies, not shared-file edits. With valid CSVs and malformed zone
GeoJSON, the normal import must fail and all snapshots must match. With valid
zones and a bins CSV whose last longitude is 999, the import must fail its
constraint check and all table contents and derived resets must roll back.

An explicit `service_zones_<digits>.csv` works under the existing generic CSV
restore contract when GeoJSON is absent. Add the GeoJSON to that same directory:
the command must report competing sources, exit 1 and preserve every table.

## Read-only database/API comparison

Run against the database used by the backend. Override URLs for this worktree's
published ports; the default below checks the normal backend and Vite proxy.
The command does not read the GeoJSON, perform migrations or change rows.

```bash
SERVICE_ZONE_API_URLS=http://127.0.0.1:8000/map-analytics/service-zones,http://127.0.0.1:5173/api/map-analytics/service-zones uv run python - <<'PY'
import json, os, sys
from urllib.request import urlopen
from sqlalchemy import text
from app.core.config import Settings
from app.infrastructure.database import create_database_engine
engine = None
try:
    engine = create_database_engine(Settings())
    with engine.connect() as connection:
        connection.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY'))
        connection.execute(text("SET LOCAL statement_timeout = '5s'"))
        rows = connection.execute(text(
            'SELECT id, zone_name, zone_number, geometry FROM service_zones ORDER BY id'
        )).mappings().all()
        for url in os.environ['SERVICE_ZONE_API_URLS'].split(','):
            with urlopen(url, timeout=30) as response:
                data = json.load(response)
            assert set(data) == {'type', 'features'} and data['type'] == 'FeatureCollection'
            assert [f['id'] for f in data['features']] == [r['id'] for r in rows]
            for feature, row in zip(data['features'], rows, strict=True):
                assert set(feature) == {'type', 'id', 'geometry', 'properties'}
                assert feature['type'] == 'Feature' and feature['geometry'] == row['geometry']
                assert feature['properties'] == {
                    'zone_name': row['zone_name'], 'zone_number': row['zone_number']}
                assert type(feature['properties']['zone_number']) is int
            print(f'PASS {url}: {len(rows)} zones; ordered IDs, every ring and exact properties match')
except Exception as error:
    print(f'FAIL: {type(error).__name__}: service-zone response comparison failed', file=sys.stderr)
    sys.exit(1)
finally:
    if engine is not None:
        engine.dispose()
PY
```

For runtime independence, start an isolated backend with `VIPTOP_DATA_DIR`
pointing to a temporary directory containing no source. Compare both responses
again: imported zones must remain available. Put a modified source in that
directory without invoking import; responses must continue matching the database.
Clear zones in the isolated database and verify HTTP 200 with empty features,
then restore the supplied dataset. Temporarily rename the zone table in that
database: the read must return HTTP 500, never source data or an empty success;
restore the table immediately. Existing bins, landfills and population endpoints
must retain their responses through these zone-only operations.

## Browser walkthrough

Open `/admin/map-analytics` with a valid basemap configuration and the imported
datasets. Use browser Network tools to count `/api/map-analytics/` requests.

1. Start a fresh page session. All four controls must be unchecked, including
   `Aptarnavimo zonos`; no dataset request occurs until selected. The existing
   `Legenda` stays unchanged and contains no service-zone swatch.
2. Enable only zones. The first request returns five polygons; compare the names
   with the source table above. At the initial Vilnius view every name is visible
   inside its shape. Check the shared translucent fill, clear boundaries and
   text halo. Click a zone, boundary and name: no zone popup or interactive
   cursor appears. For a temporary Polygon fixture with an interior ring,
   verify the hole remains unfilled and the label avoids it.
3. Toggle zones off/on. All fills, outlines and names hide/restore together;
   the API request count remains one. Pan and zoom, repeat the toggle and check
   that the map view stays fixed. Below zoom 9 names hide; closer zooms scale
   the text. Pan across tile edges: native labels may repeat on separate tile
   fragments, but collision handling must avoid unnecessary overlap.
4. Exercise the 16 subsets of the four controls. Enable zones first, then last;
   use network throttling to stagger request completion as well. The same
   relationships must hold: zone fill below population, zone outline/text above
   population, and point markers/counts above zone visuals. No toggle changes
   another checkbox or replaces the map/camera.
5. With all layers enabled, click landfill and individual bin markers, expand a
   low-zoom cluster, and open a street-level overlapping-bin group. Open a group
   member and return to its list. Toggle zones around an open unrelated popup:
   its contents remain unchanged. Click population beneath a zone name away from
   markers: population details must open. Close details with the existing close
   button or Escape.
6. Change bin waste-category filters, toggle zones and reopen the filter dialog.
   Selections and filtered bins must persist. Check filter/group behavior after
   pan and zoom with zones enabled.
7. Delay the first zone response. Verify `Kraunami duomenys…`, toggle off/on while
   pending (one shared request), and leave it off when the response completes.
   No zone visuals may appear until re-enabled; re-enable uses the cached result.
8. In an isolated environment, return a failed zone read and verify
   `Nepavyko įkelti sluoksnio.` and `Bandyti dar kartą`. Restore the endpoint and
   retry: the next request succeeds while other layers retain their state.
   Empty stored zones show `Duomenų nėra.` without breaking the basemap.
9. Repeat with a 320-pixel viewport. Controls wrap, the legend and map remain
   usable, and there is no horizontal page overflow. Navigate away and return:
   the old renderer's sources/layers are disposed and the new session starts
   unchecked.

From `frontend/`, run `npm run build` and `npm run lint` after renderer edits.
These are compilation/style checks; this feature adds no automated test suite.

## Recorded results

2026-10-10, isolated database `serv_zone_layer_verify` on PostgreSQL at localhost:5432:

- Migration upgrade/downgrade/re-upgrade passed; the table has exactly the four
  intended columns, is empty after migration and other tables retain their rows.
- Canonical local/shared sources are byte-identical to the supplied file; the
  original is retained.
- Dedicated import ran twice successfully with five distinct zone numbers.
- Fourteen invalid input variants were rejected; holes, changed membership,
  empty input and forced database-write rollback were exercised successfully.
  Four additional malformed CRS-name types returned readable errors and exit 1.
- Missing dedicated input returned exit 1 with a readable error. Unrelated
  table counts were preserved throughout dedicated replacement checks.
- Normal import populated 9,464 sites, 21,951 bins, 201,045 history records,
  203,222 schedule records and five zones. Derived resets followed existing rules.
- Zone-only, history-only/missing-zone, no-input and explicit zone-CSV imports
  produced the expected counts, warnings and exit codes. `--dir` never fell back
  to the configured directory.
- Invalid GeoJSON, a constraint-violating final CSV row and competing zone
  sources all failed without changes to counts or deterministic content hashes
  of the ten affected tables listed above.
- Direct backend (`18018`) and Vite proxy (`18019`) comparisons passed for five
  ordered IDs, exact properties and every geometry ring.
- A second native backend (`18020`) used an empty temporary data directory.
  Absent and changed-but-unimported sources left API responses unchanged.
  Empty storage returned HTTP 200 with empty features; temporarily unavailable
  storage returned HTTP 500. Restoring storage restored the same response.
  Bins, landfills and population API responses remained identical throughout.
- Final dedicated import from the configured shared directory and normal
  CSV-plus-zone import from `backend/data/` both reported five zones. The latter
  retained the collection counts recorded above and reset derived tables as
  documented; bin-population data was then rebuilt. After each import,
  direct/proxy comparisons passed. A deliberately invalid endpoint caused the
  read-only comparison command to report failure and exit 1.
- Real browser verification used Chromium with software WebGL and the Liberty
  basemap. At the initial desktop city view, all five Lithuanian names were
  readable inside their zones. Variable text anchors avoided the central
  basemap-label collision; text remains below interactive markers/counts.
  Below zoom 9 names disappeared; at close zoom native tile-fragment labels
  repeated in separate interiors without overlapping one another.
- All 16 layer-selection subsets passed grouped visibility and ordering checks.
  Zone-first and delayed zone-last attachment produced the same area/point
  ordering. Each successful dataset was requested once per session. Toggles
  preserved the same map instance and exact camera values.
- Population details opened beneath native zone text. Landfill and individual
  bin details, low-zoom cluster expansion, street-level overlapping-bin groups,
  member details/back navigation and waste-category filtering all worked.
  Zone toggles preserved unrelated popup contents and filter/source state.
- Shared pending reads, disabled-during-load completion, cached re-enable,
  Lithuanian loading/error/empty feedback and successful retry passed. A
  temporary API Polygon fixture retained its exact interior ring and rendered
  an unfilled hole. Navigating away removed its source without JavaScript
  errors; returning started a fresh unchecked session.
- Desktop, close-zoom and 320-pixel screenshots were inspected. Controls and
  legend wrapped without horizontal overflow; real drag/pan remained usable.
- `npm run build`, `npm run lint`, `git diff --check` and
  `openspec validate serv-zone-layer --strict` passed. Build retains the existing
  bundle-size advisory for the MapLibre-containing application bundle.

Docker execution was unavailable to the agent (Docker socket permissions).
Database/import verification used the same backend packages and PostgreSQL
through a native Python environment. Docker commands above are documented for
operator verification; no Docker execution result is claimed.
