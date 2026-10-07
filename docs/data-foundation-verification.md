# Manual data-foundation verification

Use an explicitly disposable PostgreSQL database, such as `viptop_verify`, for these synthetic records and controlled GIS inputs. Supply its `DATABASE_URL`; do not run failure exercises against operational data. The synchronization command is the repeatable application entry point. These procedures do not add a test framework or seed production history.

## Schema and raw records

From `backend/`, run `uv sync --locked`, `uv run alembic upgrade head`, and `uv run alembic check`. Repeat the upgrade; it should report no new revision. Inspect `\d bins`, `\d trucks`, `\d routes`, `\d route_stops`, and `\d service_events` in psql. Compare fields, types, required values, checks, indexes, generated internal identities, and externally supplied Bin IDs with the README contract. On empty disposable storage, downgrade to base and upgrade again to verify dependency ordering; this deletes records.

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
        offset = parse_qs(urlsplit(self.path).query).get('resultOffset', ['0'])[0]
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
      "properties": {"KAIKS_NR": 634, "ADRESAS": "Synthetic updated site"},
      "geometry": {"type": "Polygon", "coordinates": [[[25.2797, 54.6872]]]}
    },
    {
      "type": "Feature",
      "properties": {"KAIKS_NR": 920, "ADRESAS": null},
      "geometry": {"type": "MultiPolygon", "coordinates": [[[[25.2800, 54.6880]]]]}
    }
  ]
}
```

The deliberately minimal rings exercise first-coordinate parsing, not full geometric validity. With `DATABASE_URL` pointing at migrated verification storage, run from `backend/`:

```bash
BIN_SYNC_SOURCE_URL=http://127.0.0.1:8765/query uv run python -m app.interfaces.bin_sync
```

Expect `retrieved=2 skipped=0 upserted=2`, an address warning for site 920, and exit zero. Inspect both coordinates and repeat the command. On the verification database, begin a transaction and reuse the earlier truck, route, stop, and event inserts, then issue `COMMIT;`. Skip the earlier Bin inserts because the import already created sites 634 and 920. Commit these synthetic references only in disposable storage. Capture all four non-Bin tables and Bin values before the following exercises.

Change the fixture and invoke the command again for each case, inspecting diagnostics, exit status, and database state:

| Fixture change | Expected result |
|---|---|
| Change site's address/coordinates | Bin updated; referenced records identical |
| Omit 920 from `features` | Existing 920 unchanged |
| Set 634's address to null, whitespace, or a nontext value | Address becomes NULL; feature is not skipped |
| Add missing, boolean, fractional, out-of-integer-range, or text `KAIKS_NR` | Invalid features skipped; valid sites imported |
| Missing geometry, empty coordinates, Point, nonnumeric/boolean/out-of-range coordinate | Invalid feature skipped; existing corresponding Bin unchanged |
| Valid empty collection, or all features invalid | Warned completion, zero upserts, unchanged registry, exit zero |
| Duplicate a usable ID in one page or across pages | Entire run fails; no Bin values change |
| Error object, missing features, non-list features, or invalid JSON | Entire run fails; prior registry retained |

For pagination, add top-level `"exceededTransferLimit": true` to `0.json`, then place another FeatureCollection in `1000.json` using `"properties": {"exceededTransferLimit": true}` and an empty features list. Put a final complete collection with a distinct site ID in `2000.json` and no continuation flag. The server log must show offsets 0, 1000, and 2000 even though the earlier pages were short/empty. All valid features are published together. Delete `2000.json` to produce a later-page HTTP 503: no updates from the earlier pages should publish. Nonboolean continuation flags must fail rather than silently truncate.

For transaction rollback, prepare a complete fixture with at least 1,001 usable distinct IDs, where the first 1,000 include an existing site's changed address and the last ID already exists in storage. In another psql session on the disposable database, lock that final site's row:

```sql
BEGIN;
SELECT id FROM bins WHERE id = 920 FOR UPDATE; -- use the actual final ID
```

Invoke the import while retaining the lock. The second upsert batch should fail after the 5-second lock timeout, the command must exit nonzero, and even the changed address in the first batch must remain unchanged. In the locking session, issue `ROLLBACK;`. Inspect unrelated tables to confirm exact preservation. This verifies an actual database failure after writes were attempted, rather than only a pre-write parse failure.

Stop the fixture server with Ctrl+C, remove only its temporary directory, and restore the real source setting after these exercises.

## Startup, scheduling, and shutdown

For native verification, run from `backend/` with a migrated disposable database:

```bash
BIN_SYNC_SOURCE_URL=http://127.0.0.1:8765/query BIN_SYNC_INTERVAL_SECONDS=2 \
  sh start.sh uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Expect migration output before the server starts, one initial import before application readiness, and recurring imports after each completed attempt plus two seconds. Request `/docs` or `/openapi.json` while a periodic fixture response has `"_delay_seconds": 3`: responses should remain responsive and the fixture server must not see overlapping automatic requests. Stop with Ctrl+C during an interval wait and during a delayed import; shutdown must finish without scheduling a new run or publishing a partial transaction.

Point `BIN_SYNC_SOURCE_URL` at port 1 to check failed startup imports against populated and empty migrated verification databases. Both should serve `/docs` after logging the failure and schedule later attempts. For recovery, start with a fixture returning an error, then replace it with valid data: a later attempt should succeed. For a migration failure, use an unreachable `DATABASE_URL`: the entrypoint must exit before Uvicorn starts. Restart against populated storage and confirm raw records survive.

For Compose verification, use an isolated project name and disposable volumes, changing host port mappings with a temporary override file if the defaults are already occupied. Build/start the complete environment with `docker compose -p viptop-verify up --build`. Check the migration/import ordering in backend logs, frontend and `/docs` availability, and actual persisted live sites. `BIN_SYNC_INTERVAL_SECONDS=2` before starting Compose should reach the backend environment. Restore the 86,400-second interval afterward. Editing the backend app during `--reload` should trigger an initial import but not a lifespan migration. When using SELinux-enabled container engines, temporary verification overrides may disable container labels for the existing bind mounts without changing the project's deployment configuration.

Finally run the built backend image with no application bind mount and a reachable disposable database. Confirm migrations, entrypoint, initial import, daily scheduling, and clean shutdown are all packaged. An isolated container restart must preserve records. Remove only the verification project's containers and volumes when finished; do not remove ordinary project storage.

## Recorded implementation verification

Manual verification on 7 October 2026 used Python 3.12, PostgreSQL 17.11, and disposable databases. Container builds and Compose startup used rootless Podman's Docker-compatible API because the host Docker socket was inaccessible. Temporary port and SELinux-label overrides were confined to the verification environment.

- Empty-database migration, repeated upgrade, disposable downgrade/re-upgrade, constraint inspection, and `alembic check` passed. Synthetic SQL exercised required references, allowed values, restricted deletion, ordered stops, UTC history, and truck attribution.
- The live import retrieved/upserted 1,351 sites with zero skipped features, matching a contemporaneous GIS count request. Repeated imports retained the same site count. This count is an observation, not an application invariant.
- Controlled inputs verified both geometry mappings, invalid-feature skipping, missing-address clearing, omissions, empty/all-invalid collections, duplicate rejection, malformed responses, short/empty intermediate pages, and later-page failure.
- A held PostgreSQL row lock forced failure in the second upsert batch; earlier changes and new rows rolled back, and all four unrelated tables remained identical.
- Native startup served requests after unreachable-source imports against empty and populated registries. Shortened scheduling recovered after failures without overlapping requests. Requests remained responsive during a slow import; shutdown completed during both waiting and active-import states.
- The assembled Compose frontend and backend served HTTP 200. Migration preceded Uvicorn, the shortened interval produced later imports, and development reload imported again without rerunning migrations. The normal daily interval was restored.
- The standalone backend image contained migration assets, migrated empty storage, and imported live sites. Restart refreshed a deliberately changed Bin address while preserving every synthetic truck, route, stop, and service event. Both shutdowns completed cleanly.
- Locked dependency installation, focused Python lint, strict OpenSpec validation, and whitespace checks passed. No test framework or automated test files were added.
