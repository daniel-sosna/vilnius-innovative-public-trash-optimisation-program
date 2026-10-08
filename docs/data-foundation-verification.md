# Manual data-foundation verification

Use an explicitly disposable PostgreSQL database, such as `viptop_verify`, for these synthetic records and controlled GIS inputs. Export its accessible `DATABASE_URL`; keep the required `BIN_SYNC_SOURCE_URL` and `BIN_SYNC_HTTP_TIMEOUT_SECONDS` in the repository-root `.env` or environment. Native commands read that shared file independently of their working directory; environment variables override it, and `POSTGRES_*` keys are ignored. Preserve existing operator files. Do not run failure exercises against operational data. The synchronization command is the repeatable application entry point; its GIS client and mapping live in `app/integrations/vilnius_gis.py`. These procedures do not add a test framework or seed production history.

## Schema and raw records

From `backend/`, run `uv sync --locked`, `uv run alembic upgrade head`, and `uv run alembic check`. Repeat the upgrade; it should report no new revision. Inspect `\d bins`, `\d trucks`, `\d routes`, `\d route_stops`, and `\d service_events` in psql. Compare fields, types, required values, checks, indexes, generated internal identities, and externally supplied Bin IDs with the README contract. On empty disposable storage, downgrade to base and upgrade again to verify dependency ordering; this deletes records.

To check the additive upgrade, first migrate disposable storage to `0001`, create and commit synthetic Bin/history records, and capture all five tables. Upgrade to head: original Bin fields and all four operational tables must be identical, with both new columns null. Revision `0001` stays unchanged. On this storage only, write metadata, downgrade to `0001`, and re-upgrade: only metadata values are lost. Inspect the two nullable unrestricted TEXT columns: neither has a default, label constraint, or new index.

The following psql session creates explicitly synthetic records only within a transaction. It exercises generated IDs, default route status, multiple trips on one date, ordered stops, history with timezone offsets/ties, and truck attribution. Use an empty verification database so site IDs do not conflict with an imported registry.

```sql
BEGIN;
INSERT INTO bins (id, lat, lon, address)
VALUES (634, 54.6872, 25.2797, 'Synthetic verification site'),
       (920, 54.6880, 25.2800, NULL);
INSERT INTO trucks (name, max_bins_per_trip, available)
VALUES ('Synthetic truck', 35, true) RETURNING id AS truck_id \gset
INSERT INTO routes (service_date, truck_id)
VALUES ('2026-09-01', :truck_id) RETURNING id AS route_id \gset
INSERT INTO routes (service_date, truck_id)
VALUES ('2026-09-01', :truck_id) RETURNING id AS second_route_id \gset
INSERT INTO route_stops (route_id, bin_id, stop_order)
VALUES (:route_id, 634, 3), (:route_id, 634, 1), (:route_id, 920, 2),
       (:second_route_id, 920, 1);
INSERT INTO service_events (bin_id, service_ts, fill_level, duration, route_id)
VALUES (634, '2026-09-01T08:00:00+03:00', 'FULL', 90, :route_id),
       (634, '2026-09-04T08:00:00+03:00', 'MORE_THAN_HALF', 60, :route_id),
       (634, '2026-09-04T05:00:00Z', 'EMPTY', 0, :route_id);
SELECT id, status FROM routes ORDER BY id;
SELECT stop_order, bin_id FROM route_stops
WHERE route_id = :route_id ORDER BY stop_order;
SELECT e.id, e.service_ts, e.fill_level, e.duration, r.truck_id, t.name
FROM service_events e JOIN routes r ON r.id = e.route_id
JOIN trucks t ON t.id = r.truck_id
WHERE e.bin_id = 634 ORDER BY e.service_ts, e.id;
-- Metadata is free text, including labels outside the source maps.
UPDATE bins SET type = 'Future collection-site type',
                greening = 'Future greening description' WHERE id = 634;
SELECT id, type, greening FROM bins ORDER BY id;
UPDATE bins SET type = 'B3 (pusiau požeminiai)',
                greening = 'Taip, agentūrai ES pritarus' WHERE id = 634;
UPDATE bins SET type = NULL, greening = NULL WHERE id = 920;
SELECT id, lat, lon, address, type, greening FROM bins ORDER BY id;
-- Finish the invalid-write exercises below before rolling back these fixtures.
```

For each invalid write, use a savepoint, observe the expected PostgreSQL error, then roll back to the savepoint so the synthetic records remain available for the next exercise. For example, in the same psql transaction:

```sql
SAVEPOINT invalid_write;
INSERT INTO route_stops (route_id, bin_id, stop_order)
VALUES (:route_id, 920, 1); -- duplicate position: unique violation
ROLLBACK TO SAVEPOINT invalid_write;
RELEASE SAVEPOINT invalid_write;
```

Repeat the savepoint pattern for these inputs:

| Write | Expected rejection |
|---|---|
| Route with null or nonexistent `truck_id` | Required reference / foreign key |
| RouteStop with each null or nonexistent `route_id` and `bin_id` | Both required references / foreign keys |
| ServiceEvent with each null or nonexistent `route_id` and `bin_id` | Both required references / foreign keys |
| Null required scalar columns; omit a Bin ID | Required value; Bin has no ID generator |
| Explicit ID for an internal entity | Generated-always identity |
| Bin coordinates outside bounds, `NaN`, or infinities | Geographic checks |
| Truck capacity zero or negative | Positive-capacity check |
| Stop position zero or negative | Positive-position check |
| Route status outside the three labels | Status check |
| Event fill level outside the four labels | Observation check |
| Negative event duration | Duration check |
| Delete referenced bin 634, the fixture route, or fixture truck | Restrictive foreign keys |

Also exercise all three valid route statuses, all four valid observed fill labels, and nonnegative duration zero. Finish with `ROLLBACK;`. Row counts return to their original values; generated identity sequences can advance during rolled-back inserts.

## Manual import

From `backend/`, with the verification connection exported:

```bash
uv run python -m app.interfaces.bin_sync
uv run python -m app.interfaces.bin_sync
```

Both runs should report retrieved/skipped/upserted counts and exit zero; the second must not duplicate sites. Inspect selected coordinates and count stored sites. A count query to the live source uses `where=1=1&returnCountOnly=true&f=json`; compare to the current received count rather than hard-coding the exploration snapshot. Retained previously absent sites can make total stored rows larger than the current source count.

To observe a failure without changing the registry:

```bash
BIN_SYNC_SOURCE_URL=http://127.0.0.1:1/query uv run python -m app.interfaces.bin_sync
```

The command must return nonzero, identify retrieval failure, and retain every previous Bin value. Compare before/after database results, not just the process exit status.

## Controlled GIS responses

Use a temporary fixture directory and HTTP server to supply known inputs through the normal client. The server is only a manual verification input; it is not part of the deployed application. Run this in a separate terminal at the repository root:

```bash
export GIS_FIXTURE_DIR=$(mktemp -d /tmp/viptop-gis.XXXXXX)
python - <<'PY'
import json, os, time
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit
root = Path(os.environ['GIS_FIXTURE_DIR'])
print('Fixture directory:', root, flush=True)
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = parse_qs(urlsplit(self.path).query)
        print('Query:', query, flush=True)
        offset = query.get('resultOffset', ['0'])[0]
        path = root / (str(int(offset)) + '.json')
        if not path.exists():
            self.send_error(503, 'No fixture for requested offset')
            return
        payload = path.read_bytes()
        try:
            body = json.loads(payload)
            if isinstance(body, dict):
                time.sleep(body.pop('_delay_seconds', 0))
                payload = json.dumps(body).encode()
        except json.JSONDecodeError:
            pass
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)
ThreadingHTTPServer(('127.0.0.1', 8765), Handler).serve_forever()
PY
```

In a second terminal, use the printed fixture directory path as `GIS_FIXTURE_DIR`. Create `0.json` containing this complete synthetic collection:

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {"KAIKS_NR": 634, "ADRESAS": "Synthetic updated site", "TIPAS": 4, "ZELDINIMAS": 3},
      "geometry": {"type": "Polygon", "coordinates": [[[25.2797, 54.6872]]]}
    },
    {
      "type": "Feature",
      "properties": {"KAIKS_NR": 920, "ADRESAS": null, "TIPAS": 1, "ZELDINIMAS": null},
      "geometry": {"type": "MultiPolygon", "coordinates": [[[[25.2800, 54.6880]]]]}
    }
  ]
}
```

The deliberately minimal rings exercise first-coordinate parsing, not full geometric validity. With `DATABASE_URL` pointing at migrated verification storage, run from `backend/`:

```bash
BIN_SYNC_SOURCE_URL=http://127.0.0.1:8765/query uv run python -m app.interfaces.bin_sync
```

Expect `retrieved=2 skipped=0 upserted=2`, an address warning for site 920, and exit zero. Inspect both coordinates and metadata: site 634 must contain `B3 (pusiau požeminiai)` and `Taip, agentūrai ES pritarus`; site 920 must contain `A1 (požeminiai)` and null greening. Repeat the command. On the verification database, begin a transaction and reuse the earlier truck, route, stop, and event inserts, then issue `COMMIT;`. Skip the earlier Bin inserts because the import already created sites 634 and 920. Commit these synthetic references only in disposable storage. Capture all four non-Bin tables and Bin values before the following exercises.

Change the fixture and invoke the command again for each case, inspecting diagnostics, exit status, and database state:

| Fixture change | Expected result |
|---|---|
| Change site's address/coordinates/type/greening | Bin updated; all four referenced tables identical |
| Missing/null `TIPAS` or `ZELDINIMAS` | Corresponding metadata cleared silently; site imported |
| Unknown code 99, boolean, float (including 1.0), string, object, or array | Corresponding metadata NULL; warning shows ID, source field and raw value; site imported and exit zero |
| Write arbitrary metadata text with SQL, then import a known code | GIS label replaces manual text |
| Omit or invalidate geometry for a previously stored site | Every previous field, including metadata, retained |
| Omit 920 from `features` | Existing 920 unchanged |
| Set 634's address to null, whitespace, or a nontext value | Address becomes NULL; feature is not skipped |
| Add missing, boolean, fractional, out-of-integer-range, or text `KAIKS_NR` | Invalid features skipped; valid sites imported |
| Missing geometry, empty coordinates, Point, nonnumeric/boolean/out-of-range coordinate | Invalid feature skipped; existing corresponding Bin unchanged |
| Valid empty collection, or all features invalid | Warned completion, zero upserts, unchanged registry, exit zero |
| Duplicate a usable ID in one page or across pages | Entire run fails; no Bin values change |
| Error object, missing features, non-list features, or invalid JSON | Entire run fails; prior registry retained |

For pagination, add top-level `"exceededTransferLimit": true` to `0.json`, then place another FeatureCollection in `1000.json` using `"properties": {"exceededTransferLimit": true}` and an empty features list. Put a final complete collection with a distinct site ID in `2000.json` and no continuation flag. The server log must show offsets 0, 1000, and 2000 even though the earlier pages were short/empty. All valid features are published together. Delete `2000.json` to produce a later-page HTTP 503: no updates from the earlier pages should publish. Nonboolean continuation flags must fail rather than silently truncate.

Repeat the pagination exercise with the exact configured all-attributes query (quoted to keep shell ampersands literal):

```bash
BIN_SYNC_SOURCE_URL='http://127.0.0.1:8765/query?f=geojson&resultOffset=0&resultRecordCount=50&where=1%3D1&outFields=%2A&returnGeometry=true&outSR=4326&spatialRel=esriSpatialRelIntersects' \
  uv run python -m app.interfaces.bin_sync
```

Use `0.json`, `50.json` (empty, continuing), and `100.json` instead of 0/1000/2000. Captured requests must retain all supplied parameters plus `orderByFields=OBJECTID ASC`, with offsets 0/50/100. A configured nonzero offset must still begin at zero. Bare URLs use 1,000-record pages and select all fields. Try `resultRecordCount=0`, `1001`, `1.5`, or text: failure must precede publication. Delete the later fixture to confirm earlier metadata updates are not published.

For transaction rollback, prepare a complete fixture with at least 1,001 usable distinct IDs, where the first 1,000 include an existing site's changed address/type/greening and the last ID already exists in storage. In another psql session on the disposable database, lock that final site's row:

```sql
BEGIN;
SELECT id FROM bins WHERE id = 920 FOR UPDATE; -- use the actual final ID
```

Invoke the import while retaining the lock. The second upsert batch should fail after the 5-second lock timeout, the command must exit nonzero, and every Bin value must match its snapshot, including the first batch's address/type/greening and all newly attempted rows being absent. In the locking session, issue `ROLLBACK;`. Inspect unrelated tables to confirm exact preservation. This verifies an actual database failure after writes were attempted, rather than only a pre-write parse failure.

Stop the fixture server with Ctrl+C, remove only its temporary directory, and restore the real source setting after these exercises.

## Source metadata mapping and count interpretation

Exercise every code below by changing the synthetic fixture properties, running the normal importer, and inspecting `SELECT id, type, greening FROM bins ORDER BY id;`. These are source translations, not database allowed-value lists.

| TIPAS | Stored type |
|---|---|
| 1 | A1 (požeminiai) |
| 2 | A3 (požeminiai) |
| 3 | B2 (pusiau požeminiai stačiakampiai) |
| 4 | B3 (pusiau požeminiai) |
| 5 | C1 (pusiau požeminiai apvalūs) |
| 6 | C5 (pusiau požeminiai apvalūs) |
| 7 | D8 (dekoratyviniai apdangalai) |
| 8 | E3 (antžeminiai, pakeliamieji) |
| 9 | E4 (antžeminiai, įrengti pastate, atskirame statinyje) |
| 10 | F (pilnai nesukomplektuota aikštelė) |

| ZELDINIMAS | Stored greening |
|---|---|
| 1 | Taip |
| 2 | Ne |
| 3 | Taip, agentūrai ES pritarus |

Missing/null values produce no metadata warning. For an otherwise usable single site with both codes 99, expect two warnings and `retrieved=1 skipped=0 upserted=1`, exit zero. Malformed optional values have the same nonfatal behavior. Only invalid required identity/geometry increments skipped; unknown replacements clear previously known metadata. Upserted counts include unchanged rows. Absent/skipped sites retain existing metadata, and stored arbitrary text is overwritten by a usable GIS feature.

Inspect live or controlled results with:

```sql
SELECT id, lat, lon, address, type, greening FROM bins ORDER BY id LIMIT 10;
SELECT type, greening, count(*) FROM bins GROUP BY type, greening;
SELECT count(*) FILTER (WHERE type IS NULL) AS null_types,
       count(*) FILTER (WHERE greening IS NULL) AS null_greening FROM bins;
```

## Startup and explicit population

For native verification, run from `backend/` with the disposable connection exported and source/HTTP-timeout settings configured. There is no interval setting:

```bash
BIN_SYNC_SOURCE_URL=http://127.0.0.1:8765/query \
  sh start.sh uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Expect migration output before the server starts, `/docs` and `/openapi.json` availability, zero fixture requests, and no rows in a fresh Bin registry. Leave the application idle, restart it, and trigger reload by touching `app/main.py`: no GIS request or Bin change should occur. A reload starts another server process but does not rerun the container/native entrypoint's migration command.

In another terminal at `backend/`, export the same verification connection and explicitly populate Bins:

```bash
BIN_SYNC_SOURCE_URL=http://127.0.0.1:8765/query uv run python -m app.interfaces.bin_sync
```

The fixture log should show one complete import, including all indicated pages, followed by command exit. No further request should appear without another command invocation. Change the fixture's metadata: stored rows remain unchanged until an explicit rerun. Repeat the command to verify updates, stable IDs, and historical references.

For a slow import, add `"_delay_seconds": 5` to the fixture and run the command from the second terminal. During that separately launched process, request `/openapi.json` and stop the native server with Ctrl+C. Requests and application shutdown must not wait for the importer, which remains responsible for completing or failing its own transaction and releasing its resources. Stop or await the command separately before removing verification storage.

Point the source configuration at port 1 and start the server against empty and populated migrated storage. Both should serve requests without a source attempt or synchronization failure log. An explicitly invoked importer against that source must return nonzero and preserve stored data. For migration failure, use an unreachable `DATABASE_URL`: the entrypoint must exit before Uvicorn starts.

For Compose verification, use an isolated project and disposable volumes, changing host ports with a temporary override if necessary. Supply an explicit temporary `--env-file` containing the connection, source URL, and HTTP timeout. Verify `docker compose config` succeeds without an interval, rejects each missing required source/timeout setting, and honors shell overrides. Start the complete environment with `docker compose -p viptop-verify up --build -d` and inspect migration-before-serving logs, frontend and `/docs` availability, and an empty initial registry. Then invoke:

```bash
docker compose -p viptop-verify exec backend uv run python -m app.interfaces.bin_sync
```

Use the same env-file and override flags for every Compose command when applicable. Compare the explicit live import's retrieved count to a contemporaneous source count query and inspect mapped values. Repeat the command; existing IDs must not duplicate. Restart and development reload must preserve all stored values and generate no additional GIS requests. For controlled request capture, bind the fixture server to a host interface reachable from containers and use the engine's host gateway address in the temporary source setting (for example Podman's `host.containers.internal`, or Docker's `host.docker.internal` with a temporary `extra_hosts: ["host.docker.internal:host-gateway"]` override). Temporary SELinux-label overrides can likewise be confined to verification bind mounts. Restore the real source afterward.

Finally run the built backend image without application bind mounts or dotenv, supplying all three required settings through its environment. Confirm revision `0002`, `app/integrations/vilnius_gis.py`, and absence of `.env` are packaged. Start against fresh migrated storage: the registry stays empty until explicit command invocation. Inspect a synthetic historical snapshot and manually changed Bin metadata through a restart: all values must remain unchanged, with no GIS request. An explicit refresh can then restore authoritative source metadata without altering history. Stop the server normally and remove only owned verification containers/volumes.

## Historical automatic-import verification (superseded)

The results below describe the previous automatic-import lifecycle. Current startup and import behavior is defined in the procedures above and the manual-only verification record below.

Manual verification on 7 October 2026 used Python 3.12, PostgreSQL 17.11, and disposable databases. Container builds and Compose startup used rootless Podman's Docker-compatible API because the host Docker socket was inaccessible. Temporary port and SELinux-label overrides were confined to the verification environment.

- Empty-database migration, repeated upgrade, disposable downgrade/re-upgrade, constraint inspection, and `alembic check` passed. Synthetic SQL exercised required references, allowed values, restricted deletion, ordered stops, UTC history, and truck attribution.
- The live import retrieved/upserted 1,351 sites with zero skipped features, matching a contemporaneous GIS count request. Repeated imports retained the same site count. This count is an observation, not an application invariant.
- Controlled inputs verified both geometry mappings, invalid-feature skipping, missing-address clearing, omissions, empty/all-invalid collections, duplicate rejection, malformed responses, short/empty intermediate pages, and later-page failure.
- A held PostgreSQL row lock forced failure in the second upsert batch; earlier changes and new rows rolled back, and all four unrelated tables remained identical.
- Native startup served requests after unreachable-source imports against empty and populated registries. Shortened scheduling recovered after failures without overlapping requests. Requests remained responsive during a slow import; shutdown completed during both waiting and active-import states.
- The assembled Compose frontend and backend served HTTP 200. Migration preceded Uvicorn, the shortened interval produced later imports, and development reload imported again without rerunning migrations. The normal daily interval was restored.
- The standalone backend image contained migration assets, migrated empty storage, and imported live sites. Restart refreshed a deliberately changed Bin address while preserving every synthetic truck, route, stop, and service event. Both shutdowns completed cleanly.
- Locked dependency installation, focused Python lint, strict OpenSpec validation, and whitespace checks passed. No test framework or automated test files were added.

### Bin metadata verification — 8 October 2026

The metadata change was manually verified with Python 3.12 and disposable PostgreSQL 17 storage. The complete Compose environment and standalone backend image ran through rootless Podman's Docker-compatible API, with temporary host ports and SELinux-label overrides confined to verification.

- Settings loaded an isolated repository-root dotenv from multiple working directories, ignored shared `POSTGRES_*` keys, honored environment overrides, and worked without dotenv when all values were supplied. Missing settings and invalid URLs/numbers failed with credential-safe diagnostics. Compose rejected each missing sync setting and accepted explicit env files/shell overrides. The documented native `uv run` migration/import commands resolved root dotenv settings with only a localhost connection exported.
- Fresh and populated upgrades to `0002`, repeated upgrades, `alembic check`, and disposable downgrade/re-upgrade passed. Exactly two nullable TEXT columns without defaults were added; original Bin fields and all four operational tables remained identical. SQL accepted arbitrary metadata, Lithuanian labels, and nulls while existing coordinate/reference constraints remained enforced.
- Direct client requests retained the supplied query, stable ordering, and 50-record pagination. Offset reset, both continuation locations, short/empty intermediate pages, bare-endpoint defaults, unsupported sizes, duplicate IDs, and later-page failure were checked.
- All ten TIPAS and three ZELDINIMAS labels were checked in the mapper and through the actual importer into PostgreSQL. Missing/null codes were silent; unknown numbers, booleans, floats, strings, objects, and arrays yielded null with site/field/raw-value warnings without rejecting the site. Both geometry forms retained longitude/latitude order.
- CLI imports updated/cleared metadata, overwrote manually entered free text, retained absent/skipped sites, and preserved exact synthetic historical records. Unknown warnings returned exit zero with zero skipped features. A later-page failure and a row lock in the second 1,000-row SQL batch returned nonzero and preserved every prior Bin value; attempted new rows rolled back.
- Live startup retrieved/upserted 1,351 sites, zero skipped, matching a contemporaneous count query. The first 50 source records matched all stored fields exactly; 178 types and 740 greening values were null. Repeat import produced identical records. These counts are observations, not fixed acceptance criteria.
- Compose frontend/backend returned HTTP 200 with migration preceding startup import. A two-second schedule applied later controlled metadata changes; an OpenAPI request during a three-second import delay took approximately 0.006 seconds. Shutdown completed cleanly, then the real source and 86,400-second interval were restored and the final backend rebuilt.
- The image contained revision `0002`, used environment-only settings without mounts or dotenv, migrated/imported 1,351 sites, and preserved all synthetic truck/route/stop/event records across restart while refreshing authoritative metadata. Both image shutdowns completed cleanly. Disposable containers and database/Compose volumes were removed.
- Focused Python lint, strict OpenSpec validation, and whitespace checks passed. Revision `0001`, dependencies, governance, and frontend code were unchanged; no automated test files were added.


## Manual-only import verification — 8 October 2026

These results verify the revised explicit-import lifecycle with Python 3.12 and disposable PostgreSQL 17 storage. Container checks used rootless Podman's Docker-compatible API; port and SELinux-label overrides were limited to the verification environment. Previous automatic-import results above are historical.

- Settings and Compose loaded without an interval, retained the required source/HTTP-timeout values, and honored root dotenv/environment precedence. Shared PostgreSQL keys and obsolete interval keys were ignored. Missing/invalid required inputs produced credential-safe errors. The documented native migration/import commands resolved root dotenv settings with only the accessible database connection exported.
- The relocated `app.integrations.vilnius_gis` module and the actual CLI retrieved controlled short/empty multi-page responses and mapped metadata correctly. Unknown type warnings returned exit zero with zero skipped features. Synthetic history stayed identical through repeat imports, and later-page and second SQL batch lock failures preserved all prior Bin values and rolled back attempted new rows.
- Native startup, idle runtime, development reload, and an unavailable-source restart made zero GIS requests. The explicit slow command ran one import and exited; the server served OpenAPI during the delay and shut down in approximately 0.166 seconds without waiting for that separately launched command.
- Complete Compose startup served frontend and backend HTTP 200 after migrations with an empty registry and zero GIS requests, including slow and unavailable configured sources. Explicit live import retrieved/upserted 1,351 sites with zero skipped, matching a contemporaneous source count. The first 50 source records matched every stored field, with 178 null types and 740 null greening values across the registry. A repeat import produced identical records; these counts are observations, not constants.
- Compose restart, reload, and idle runtime preserved all stored Bin values and made no GIS requests. Changing a controlled source alone did not refresh metadata; an explicit command did. The server remained responsive during a separately launched slow native importer and shut down in approximately 0.281 seconds while the command continued to completion. The real source configuration was restored afterward.
- The standalone rebuilt image ran without bind mounts, dotenv, or an interval setting. It packaged migration `0002` and the relocated integration, prepared empty tables without GIS access, and imported only through the explicit CLI. Stop/start preserved manually changed Bin values and every synthetic truck/route/stop/event record without refreshing metadata; an explicit rerun restored authoritative metadata while preserving history. Both normal shutdowns completed cleanly. Rootless-engine checks used explicit stop/start to capture graceful shutdown reliably.
- Focused Python lint, strict OpenSpec validation, and whitespace checks passed. Migrations, persistence contracts, dependencies, frontend, and governance remained unchanged by the lifecycle revision; no automated test files were added. All owned verification containers and database/Compose volumes were removed, while the pre-existing build cache was retained.
