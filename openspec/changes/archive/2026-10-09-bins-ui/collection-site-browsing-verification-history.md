# Historical isolated verification

This records pre-activation evidence only. The user confirmed import finished on
2026-10-09 and authorized transfer to the main checkout and real Compose. The
verification overrides and temporary path pointer were removed. Old startup and
cleanup commands below are historical and must not be used. Current commands are
in [collection browsing verification](collection-site-browsing-verification.md).

# Collection browsing verification

## Current evidence (2026-10-09, Europe/Vilnius)

Tasks 1.2 and 1.3 prepare a separate verification runtime. Tasks 2.1–2.6 and 3.1–3.5 now have implementation code and documentation in the isolated checkout. Task 3.2's dependency/build checks passed and it is checked. Tasks requiring live storage/container verification remain unchecked; see the detail evidence below. No verification container was built or started. Child bins and history now have implementation for tasks 4.1–4.6. Frontend tasks 4.2, 4.4 and 4.5 passed synthetic browser checks; the read-only procedure for task 4.6 is documented below. Required real HTTP/SQL checks for 4.1 and 4.3 remain unmet.

Docker Compose v5.6.0 successfully resolved the temporary override. The configuration check used a synthetic connection (`config_check` credentials at `db:5432/viptop`) and `unverified-existing-database-network`. These values demonstrate configuration shape only; they are not a verified connection or network. The real connection and network are required inputs before startup.

- Project: `viptop-bins-ui-verification`.
- Services: `bins-ui-backend`, `bins-ui-frontend`; no PostgreSQL service or service dependencies.
- Images: `viptop-bins-ui-backend:verification`, `viptop-bins-ui-frontend:verification`.
- Intended container names: `viptop-bins-ui-verification-backend`, `viptop-bins-ui-verification-frontend`; owner label `viptop.verification.owner=bins-ui`.
- Dependency volumes: `viptop-bins-ui-verification_bins_ui_backend_venv`, `viptop-bins-ui-verification_bins_ui_frontend_node_modules`.
- Bind mounts and build contexts: only the isolated checkout's `backend/` and `frontend/` directories. Bind mounts disable automatic creation of missing host directories.
- Ports: `127.0.0.1:8001 -> 8000` and `127.0.0.1:5174 -> 5173`. Both host ports had no listeners at inspection time; recheck before starting.
- Backend entrypoint: `/app/.venv/bin/uvicorn`; arguments `app.main:app --host 0.0.0.0 --port 8000`. It bypasses `start.sh`, Alembic, import and reload. The dedicated dependency volume is populated from the newly built image.
- Frontend proxy: `http://bins-ui-backend:8000` on the new project's private default network. Only the new backend also joins the existing database's external network. Its distinct service name avoids publishing another `backend` alias on the operational network.
- Map style startup input: `BINS_UI_MAP_STYLE_URL` sets `VITE_MAP_STYLE_URL`, defaulting to `https://tiles.openfreemap.org/styles/liberty` in this override. The map component reads only the Vite variable; there is no component fallback.

The override replaces the service/volume/network maps with the verification subset while reusing the repository's Dockerfiles and application startup conventions. It uses Compose's [documented `!override` merge behavior](https://docs.docker.com/reference/compose-file/merge/), requiring Compose 2.24.4 or newer. No permanent Compose file was edited.

Files:

- Isolated checkout: `/home/stitas/.local/share/viptop-isolated/bins-ui`.
- Reviewable override: `openspec/changes/bins-ui/verification.compose.yaml`.
- Prepared temporary copy: `/tmp/viptop-bins-ui-verification-qqbzy83v/compose.override.yaml` (temporary files may disappear; recreate as shown below).
- Sanitized configuration evidence: `openspec/changes/bins-ui/configuration-evidence.json`.
- Original runtime/source-mount evidence: `openspec/changes/bins-ui/isolation-preflight.md`.

Docker inspection still failed with `permission denied while trying to connect to the docker API at unix:///var/run/docker.sock`; `sudo -n docker ps` reported `sudo: a password is required`. Socket/daemon permissions and existing services were not changed. Readable `/proc` mount tables still place the isolated checkout outside operational source mounts. Vite PID 493715, Uvicorn PID 493931, importer PID 678068 and PostgreSQL PID 493638 remained present in their original container cgroups. Their observed IDs are recorded in the preflight; process presence does not establish database health or continued import progress.

**Unmet live checks:** new image builds, new container IDs/startup, HTTP endpoints, actual database/network connectivity, read-only query results and import progress. Task 1.3 follows its explicit no-access branch: document these limits and continue independent configuration/documentation work. None of these live checks is reported as passed.

## Restrictions and ownership

Use only existing-schema read access. Do not run migrations, import commands, fixture inserts (even rolled back), cleanup queries, table resets or truck CRUD. Do not copy implementation into operational source mounts, change the root `.env`, reuse operational dependency volumes, start another PostgreSQL server or mount its data volume.

The owner of this verification session may build/start only the two additional application containers below and clean up only their exactly identified names/IDs after checking ownership. Existing frontend/backend/PostgreSQL/import containers, PostgreSQL storage and shared networks belong to the operational environment and must stay intact. Do not use Compose `up`, `down`, `restart`, `--remove-orphans`, volume removal or network removal as part of this procedure.

## Prepare and validate (does not start containers)

Run from the isolated checkout. If Docker access remains unavailable, stop before the build/start sections and record the access error; offline configuration validation remains available. Do not change infrastructure to obtain access.

```bash
cd /home/stitas/.local/share/viptop-isolated/bins-ui
export BINS_UI_CHECKOUT="$PWD"
export BINS_UI_RUNTIME_DIR="$(mktemp -d /tmp/viptop-bins-ui-verification-XXXXXX)"
cp openspec/changes/bins-ui/verification.compose.yaml "$BINS_UI_RUNTIME_DIR/compose.override.yaml"

bins_ui_compose() {
  docker compose --project-name viptop-bins-ui-verification \
    --env-file "$BINS_UI_CHECKOUT/.env.example" \
    -f "$BINS_UI_CHECKOUT/docker-compose.yml" \
    -f "$BINS_UI_RUNTIME_DIR/compose.override.yaml" "$@"
}
```

For offline validation only, use these explicitly synthetic values in a subshell:

```bash
(
  export BINS_UI_DB_NETWORK=unverified-existing-database-network
  export BINS_UI_DATABASE_URL=postgresql+psycopg://config_check:config_check@db:5432/viptop
  bins_ui_compose config --quiet
  bins_ui_compose config --services
  bins_ui_compose config --volumes
)
```

Before runtime use, inspect the current PostgreSQL container and confirm its network, connection hostname/port/database and current source mounts. Do not assume the Compose-derived network name or `db` alias exists. The PostgreSQL container ID observed during preflight was `2e2c4be9479ed1c17b856d1b78a48571702cad81ad2f786d9992e98e25d8dc44`:

```bash
docker ps --no-trunc --format '{{.ID}} {{.Names}} {{.Status}}'
docker inspect --format '{{json .NetworkSettings.Networks}}' \
  2e2c4be9479ed1c17b856d1b78a48571702cad81ad2f786d9992e98e25d8dc44
read -rp 'Inspected existing PostgreSQL network: ' BINS_UI_DB_NETWORK
export BINS_UI_DB_NETWORK
read -rsp 'Existing postgresql+psycopg connection URL: ' BINS_UI_DATABASE_URL
export BINS_UI_DATABASE_URL
export BINS_UI_MAP_STYLE_URL=https://tiles.openfreemap.org/styles/liberty
docker network inspect "$BINS_UI_DB_NETWORK" --format '{{.Id}} {{.Name}}'
```

The URL must target the existing database using a hostname reachable from that network. Do not display credentials, dump container environments or commit private connection files. The `.env.example` passed to Compose supplies public interpolation defaults for the base file; it is not copied into either container and does not select the verification database.

Validate the actual resolved configuration without printing its private environment. This repeatable inline check exits nonzero on invalid configuration or an isolation mismatch:

```bash
python3 - <<'PY'
import json, os, subprocess
from pathlib import Path

root = Path(os.environ['BINS_UI_CHECKOUT']).resolve()
runtime = Path(os.environ['BINS_UI_RUNTIME_DIR'])
result = subprocess.run([
    'docker', 'compose', '--project-name', 'viptop-bins-ui-verification',
    '--env-file', str(root / '.env.example'),
    '-f', str(root / 'docker-compose.yml'),
    '-f', str(runtime / 'compose.override.yaml'), 'config', '--format', 'json',
], capture_output=True, text=True)
if result.returncode:
    raise SystemExit('FAIL: Compose configuration rejected; check required inputs privately.')
config = json.loads(result.stdout)
assert config['name'] == 'viptop-bins-ui-verification'
assert set(config['services']) == {'bins-ui-backend', 'bins-ui-frontend'}
assert set(config['volumes']) == {'bins_ui_backend_venv', 'bins_ui_frontend_node_modules'}
assert config['networks']['existing_database']['external'] is True
assert config['networks']['existing_database']['name'] == os.environ['BINS_UI_DB_NETWORK']
for name, service in config['services'].items():
    component = name.removeprefix('bins-ui-')
    assert service['build']['context'] == str(root / component)
    assert service['image'] == f'viptop-bins-ui-{component}:verification'
    assert not service.get('depends_on')
    assert len(service['ports']) == 1
    port = service['ports'][0]
    assert port['host_ip'] == '127.0.0.1'
    assert port['published'] == ('8001' if component == 'backend' else '5174')
    assert len(service['volumes']) == 2
    for volume in service['volumes']:
        if volume['type'] == 'bind':
            assert volume['source'] == str(root / component)
            assert volume['target'] == '/app'
            assert volume['bind']['create_host_path'] is False
        else:
            expected = 'bins_ui_backend_venv' if component == 'backend' else 'bins_ui_frontend_node_modules'
            assert volume['source'] == expected
            assert config['volumes'][expected]['name'] == f'viptop-bins-ui-verification_{expected}'
    startup = ' '.join((service.get('entrypoint') or []) + (service.get('command') or []))
    assert all(word not in startup for word in ('start.sh', 'alembic', 'bin_sync', '--reload'))
backend = config['services']['bins-ui-backend']
frontend = config['services']['bins-ui-frontend']
assert backend['entrypoint'] == ['/app/.venv/bin/uvicorn']
assert backend['environment']['DATABASE_URL'] == os.environ['BINS_UI_DATABASE_URL']
assert frontend['environment']['VIPTOP_API_PROXY_TARGET'] == 'http://bins-ui-backend:8000'
assert set(frontend['networks']) == {'default'}
assert set(backend['networks']) == {'default', 'existing_database'}
print('PASS: two isolated applications; no database service/storage/dependencies or migration/import startup.')
PY
```

## Start only the owned additional applications

Execute only after access, existing network/database identity and resolved configuration are verified. Recheck ports with `ss -ltn '( sport = :5174 or sport = :8001 )'`; output must contain no listener rows. Confirm the intended container names and image tags are unused or already belong to this session. Check dependency volumes are new or owned by this same project and do not alias operational volumes.

Save a read-only baseline of the operational containers before startup, then recheck the same IDs, running state and start times afterward:

```bash
docker inspect --format '{{.Id}} {{.State.Running}} {{.State.StartedAt}}' \
  9839af4607ca7fe76252728ac5d9907b73e8e03c962180fba402c19698de47c5 \
  88e61d3936a9fbbaf48c5794c503a6f2f9578a3d2b2a2b2ab3066abc576ecdd5 \
  2e2c4be9479ed1c17b856d1b78a48571702cad81ad2f786d9992e98e25d8dc44 \
  > "$BINS_UI_RUNTIME_DIR/operational-before.txt"
bins_ui_compose build bins-ui-backend bins-ui-frontend
bins_ui_compose run --detach --no-deps --service-ports --use-aliases \
  --name viptop-bins-ui-verification-backend bins-ui-backend
bins_ui_compose run --detach --no-deps --service-ports --use-aliases \
  --name viptop-bins-ui-verification-frontend bins-ui-frontend
```

Record the returned new container IDs. Inspect both by those IDs, filtering for identity, owner label, project, image, entrypoint/arguments, mounts, published ports and networks; do not print `.Config.Env`. Check that all source/dependency mounts and startup commands match the validated configuration. Confirm `--use-aliases` made `bins-ui-backend` reachable for the frontend proxy. Never stop an existing container to free a name or port.

Expected endpoints after startup are `http://127.0.0.1:5174/`, `http://127.0.0.1:8001/docs` and same-origin API proxy `/api/...`. Initial GET-only connectivity checks:

```bash
curl --fail --silent --show-error --max-time 10 http://127.0.0.1:8001/openapi.json > "$BINS_UI_RUNTIME_DIR/openapi.json"
curl --fail --silent --show-error --max-time 10 http://127.0.0.1:5174/ > /dev/null
curl --fail --silent --show-error --max-time 10 'http://127.0.0.1:5174/api/trucks?page=1' > "$BINS_UI_RUNTIME_DIR/trucks-page.json"
```

These initial checks cover the existing application. Use the feature requests below for the new collection routes. Inspect startup evidence for absent migrations/import, and repeat the operational baseline command into `operational-after.txt`; `diff -u` must show no identity/running/start-time changes. Recheck the importer process separately without invoking it.

For actual storage identity and collection counts, run only this bounded read transaction in the **new** backend:

```bash
docker exec -i viptop-bins-ui-verification-backend /app/.venv/bin/python - <<'PY'
from sqlalchemy import text
from app.core.config import Settings
from app.infrastructure.database import create_database_engine

engine = create_database_engine(Settings())
try:
    with engine.connect() as connection:
        connection.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY'))
        connection.execute(text("SET LOCAL statement_timeout = '5s'"))
        connection.execute(text("SET LOCAL lock_timeout = '1s'"))
        identity = connection.execute(text("SELECT current_database() AS database, inet_server_addr() AS server, inet_server_port() AS port, current_setting('transaction_read_only') AS read_only")).mappings().one()
        assert identity['read_only'] == 'on'
        print(dict(identity))
        counts = connection.execute(text('SELECT (SELECT count(*) FROM sites) AS sites, (SELECT count(*) FROM bins) AS bins')).mappings().one()
        print(dict(counts))
        connection.rollback()
finally:
    engine.dispose()
PY
```

Compare the reported database/server/port with the inspected existing PostgreSQL identity. Record actual counts separately from synthetic examples; import may change counts between requests. This does not alter the shared engine/session configuration. New browsing request transaction protection belongs to task 2.1. A timeout or failure is an unmet check, not permission to change schema or insert fixtures.

## Site list and overview contract

Backend routes are GET-only `/sites` and `/sites/stats`; Vite exposes them as
`/api/sites` and `/api/sites/stats`. The static statistics route is registered
before the dynamic detail route. No collection mutation, model, migration, importer
or global database configuration changes are included.

`GET /sites` accepts `page` (default 1, minimum 1), `page_size` (default 15,
range 1–100) and optional `address`. The address is trimmed and matched using
literal case-insensitive SQL ILIKE: backslash, `%` and `_` are escaped. Blank
search has no condition. Items expose only integer `id`, text `address` and
integer `bin_count`, sorted by ascending site ID. Metadata is `total`, `page`,
`page_size`. A valid page beyond the result set returns empty items, preserving
the filtered total. The service skips OFFSET altogether for out-of-range pages,
including extremely large positive Python integers.

The list executes a filtered site count, a LIMIT/OFFSET site page, then one bin
count grouped only over the page's IDs. Empty/out-of-range pages need only the
count query. Zero-bin sites remain present with `bin_count: 0`. No ORM relationship,
history rows, whole-registry materialization or per-row bin query is used.

`GET /sites/stats` has no address/page parameters. It returns integer
`total_sites`, integer `total_bins`, numeric-or-null `total_capacity_m3` and
`bins_by_waste_type: [{waste_type, count}]`, ordered by raw waste-type text.
Site counts, bin count/capacity and waste groups use three independent aggregate
queries, without joins. SUM runs on the existing NUMERIC column; no COALESCE,
unit conversion or stored-value rounding is applied. A SQL NULL sum stays JSON
null, while Decimal zero becomes JSON numeric zero. `m³` is the inherited,
unverified capacity-unit assumption.

Each request configures `REPEATABLE READ, READ ONLY` before data queries, then
local statement/lock timeouts of 5s/1s. The dependency rolls back on success or
failure and closes its session before response delivery. Persistence failures
produce generic `500 {"detail":"Collection read failed"}`; logs contain the
exception class only. A snapshot belongs to one request; import can change
counts between separate HTTP/SQL requests.

## Repeatable HTTP checks after safe separate-server startup

Run only after the new server identity and existing-storage connection have been
verified above. These commands deliberately target port 8001, never operational
port 8000. Curl exits nonzero for transport errors or non-2xx responses; response
files retain actual returned values for inspection.

```bash
curl --fail --silent --show-error --max-time 10 \
  http://127.0.0.1:8001/sites > "$BINS_UI_RUNTIME_DIR/sites-page.json"
curl --fail --silent --show-error --max-time 10 \
  'http://127.0.0.1:8001/sites?page=2&page_size=7' > "$BINS_UI_RUNTIME_DIR/sites-custom-page.json"
curl --fail --silent --show-error --max-time 10 \
  http://127.0.0.1:8001/sites/stats > "$BINS_UI_RUNTIME_DIR/sites-stats.json"
```

This inline command prints useful page/stats values and exits 1 on an assertion,
HTTP or transport failure. It writes no data and requires only Python's standard
library. Substitute a known address substring through `BINS_UI_VERIFY_ADDRESS`
to exercise real matches; do not invent fixture rows. `%`/`_`/backslash results
must be compared with the literal SQL reads below, even if all return zero.

```bash
python3 - <<'PY'
import json, os
from urllib.parse import urlencode
from urllib.request import urlopen
from urllib.error import HTTPError

base = 'http://127.0.0.1:8001'
def read(path, params=None):
    url = base + path + ('?' + urlencode(params) if params else '')
    with urlopen(url, timeout=10) as response:
        return json.load(response)

schema = read('/openapi.json')
for path in ('/sites', '/sites/stats'):
    assert set(schema['paths'][path]) == {'get'}
assert not schema['paths']['/sites/stats']['get'].get('parameters')
for params in ({}, {'page': 2, 'page_size': 7},
               {'address': '   '}, {'address': '%'}, {'address': '_'},
               {'address': '\\'},
               {'address': os.environ.get('BINS_UI_VERIFY_ADDRESS', 'Vilniaus')},
               {'page': 10**30}):
    data = read('/sites', params)
    assert data['page'] == params.get('page', 1)
    assert data['page_size'] == params.get('page_size', 15)
    assert len(data['items']) <= data['page_size']
    ids = [item['id'] for item in data['items']]
    assert ids == sorted(ids)
    assert all(set(item) == {'id', 'address', 'bin_count'} for item in data['items'])
    assert all(isinstance(item['bin_count'], int) for item in data['items'])
    if params.get('page', 1) == 10**30:
        assert data['items'] == []
    print(params, data)
for params in ({'page': 0}, {'page': -1}, {'page': 'abc'},
               {'page_size': 0}, {'page_size': 101}, {'page_size': 'abc'}):
    try:
        read('/sites', params)
    except HTTPError as error:
        assert error.code == 422
        print('PASS 422:', params)
    else:
        raise AssertionError(('Expected 422', params))
stats = read('/sites/stats')
assert sum(group['count'] for group in stats['bins_by_waste_type']) == stats['total_bins']
assert stats['total_capacity_m3'] is None or isinstance(stats['total_capacity_m3'], (int, float))
print('Global overview:', stats)
print('PASS: HTTP list/stats contract; compare values with bounded read-only SQL.')
PY
```

## Repeatable SQL checks and timings on current storage

Use only the newly identified backend container. All SQL below runs in one
read-only snapshot with finite timeouts; failures exit nonzero with a sanitized
error. It prints aggregate values, ordered pages, grouped page-bin counts,
literal-match totals, and milliseconds per query. Record outputs and timestamps;
do not assert cross-request count equality while import is committing.

```bash
docker exec -i viptop-bins-ui-verification-backend /app/.venv/bin/python - <<'PY'
from time import perf_counter
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from app.core.config import Settings
from app.infrastructure.database import create_database_engine

engine = create_database_engine(Settings())
try:
    with engine.connect() as connection:
        connection.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY'))
        connection.execute(text("SET LOCAL statement_timeout = '5s'"))
        connection.execute(text("SET LOCAL lock_timeout = '1s'"))
        def query(label, sql, params=None):
            start = perf_counter()
            rows = connection.execute(text(sql), params or {}).mappings().all()
            print(label, [dict(row) for row in rows], f'{(perf_counter()-start)*1000:.2f} ms')
            return rows
        query('Settings', "SELECT current_setting('transaction_isolation') AS isolation, current_setting('transaction_read_only') AS read_only, current_setting('statement_timeout') AS statement_timeout, current_setting('lock_timeout') AS lock_timeout")
        query('Sites', 'SELECT count(*) AS total_sites FROM sites')
        query('Bins/capacity', 'SELECT count(*) AS total_bins, sum(capacity_m3) AS total_capacity_m3 FROM bins')
        query('Waste groups', 'SELECT waste_type, count(*) AS count FROM bins GROUP BY waste_type ORDER BY waste_type')
        for page, size in ((1, 15), (2, 7)):
            rows = query(f'Page {page}/{size}', 'SELECT id, address FROM sites ORDER BY id LIMIT :size OFFSET :offset', {'size': size, 'offset': (page-1)*size})
            if rows:
                query('Page bin counts', 'SELECT site_id, count(*) AS bin_count FROM bins WHERE site_id = ANY(:ids) GROUP BY site_id ORDER BY site_id', {'ids': [row['id'] for row in rows]})
        for value in ('%', '_', '\\', 'Vilniaus'):
            escaped = value.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
            params = {'pattern': '%' + escaped + '%'}
            query(f'Literal {value!r}', "SELECT count(*) AS total FROM sites WHERE address ILIKE :pattern ESCAPE '\\'", params)
            query(f'Literal page {value!r}', "SELECT id, address FROM sites WHERE address ILIKE :pattern ESCAPE '\\' ORDER BY id LIMIT 15", params)
        query('Missing-capacity availability', 'SELECT count(*) FILTER (WHERE capacity_m3 IS NULL) AS null_capacity_bins, count(*) FILTER (WHERE capacity_m3 = 0) AS zero_capacity_bins FROM bins')
        query('Zero-bin availability', 'SELECT count(*) AS zero_bin_sites FROM sites s WHERE NOT EXISTS (SELECT 1 FROM bins b WHERE b.site_id = s.id)')
        query('Page plan', 'EXPLAIN SELECT id, address FROM sites ORDER BY id LIMIT 15 OFFSET 15')
        connection.rollback()
except SQLAlchemyError as error:
    raise SystemExit(f'FAIL: read-only verification ({type(error).__name__}); no SQL or credentials logged.') from None
finally:
    engine.dispose()
PY
```

A 5s timeout is a failed live check. Report it and the query area; do not add
indexes, alter timeouts globally or change import to obtain passing output.
If no zero-capacity/zero-bin/literal-character rows exist, record that absence
rather than inserting fixtures. Unknown/empty capacity and empty-registry
backend behavior remains unverified on live data unless actual records cover it.

## UI procedure and current implementation evidence

On the separate frontend at `http://127.0.0.1:5174/admin/sites`, check the navbar
at desktop and 320px, the 15-row list, next/page-jump controls, and address
search from page 2. Search must request page 1. Hover/focus a full-row link;
its icon appears and activation goes to the same-tab `/admin/sites/{id}`.
The detail destination is now implemented by group 3. Verify it using the detail
procedure below; the older group 2 evidence is limited to list navigation.

Filter/paging must leave overview values unchanged and must not request
statistics again. Force each data area's request failure locally and retry it:
overview retry must not refetch the list, and list retry must not refetch
statistics. Verify nonmatching addresses have a clear-filter action; unfiltered
empty data has `Surinkimo vietų dar nėra.`. Delay one search response and replace
the search before it finishes: the old response must not replace the current row.

Observed offline evidence on 2026-10-09:

- Isolated `uv sync --locked` and `npm ci` passed without changing lockfiles.
- OpenAPI/schema checks passed for GET-only routes, default page 1/size 15,
  1–100 size bounds, response fields and numeric/null capacity serialization.
- In-process ASGI HTTP checks with offline session doubles passed for 200 list
  and overview responses, invalid-page/size 422 responses, an extremely large
  positive page, per-request setup/rollback and sanitized setup-failure 500.
  These are synthetic HTTP checks, not requests to existing storage.
- An offline session double checked the dependency's transaction-setting order,
  rollback and generic persistence errors, including setup/rollback/close
  failure. It does not
  establish live PostgreSQL settings.
- PostgreSQL query compilation plus synthetic read-result checks passed for
  trimmed literal `%`/`_`/backslash filtering, blank search, ascending ordering,
  page sizes, huge/empty pages, page-only grouped bin counts and zero-bin sites.
  There are at most three data queries per nonempty list page, with no N+1.
- Synthetic aggregate-result checks confirmed independent site/bin totals, no
  joins, NUMERIC SQL SUM, known zero and NULL preservation. No live timings exist.
- `npm run lint`, `npm run build`, focused Python compilation and Ruff checks
  passed. No automated test files were added.
- Standalone browser checks used only intercepted synthetic responses on the
  isolated preview; every `/api/**` request was intercepted, including unused
  paths. The preview proxy targeted unused port 8001, not operational port 8000.
  Synthetic values were 31 sites, 62 bins, capacity 3.6, and category counts
  30/20/12; these are **not observed database totals**.
- Synthetic browser checks covered default 15 rows, page 2, search/reset,
  clearing no-match results, cancellation of a delayed older search, independent
  list/overview retry and unchanged global overview while filtering/paging.
  Category labels/counts, zero-capacity `0 m³`, NULL `N/A`, zero-bin empty donut,
  keyboard-focus icon and responsive navbar at 320px were checked.
- Follow-up synthetic checks passed for keyboard and touch row activation to
  the detail URL, mobile-menu selection/closing, the unfiltered empty-registry
  message and disabled pagination. The destination remains the existing
  page-not-found screen at the time of those group 2 checks; detail evidence is
  recorded separately below.
- Desktop/mobile screenshots were inspected at `/tmp/bins-ui-list-desktop.png`
  and `/tmp/bins-ui-list-mobile.png`. These temporary screenshots may disappear.
- All 136 files in the operational-source baseline still match their recorded
  SHA-256 digests. The four previously observed Vite/Uvicorn/import/PostgreSQL
  PIDs remain present. Process presence does not prove import progress or health.
- Syntax checks passed for all 12 documented Bash blocks and four inline Python
  commands, without running the Docker/database commands. The native isolated
  preview was stopped after browser verification; no application containers
  were created, stopped or modified.

**Unmet live evidence for tasks 2.1–2.6:** real HTTP response values, per-request
PostgreSQL settings, literal-match comparisons against current storage, global
aggregate comparisons/timings, UI against the real API, available edge-case
records and startup/import continuity. Docker access is still denied; no new
verification containers were started. The six task checkboxes stay pending
because their requested verification includes these unavailable checks. This
records implemented code separately from completed, verified tasks.

## Site detail contract and map configuration

`GET /sites/{site_id}` is GET-only, uses the same short read-only snapshot and
returns a flat object with `id`, `address`, nullable numeric `latitude` and
`longitude`, nullable text `sub_district`, `street`, `house_number`, `postal_code`,
integer `bin_count`, numeric-or-null `total_capacity_m3`, `object_groups: string[]`
and `waste_carriers: string[]`. No nested bins or history are fetched or returned.
The static `/sites/stats` route precedes this route. Positive absent IDs return
404; invalid/nonpositive IDs return 422. Positive IDs beyond PostgreSQL BIGINT
range return 404 without passing an overflowing parameter to storage.

All four location text fields come from exactly one bin selected by
`ORDER BY bins.id LIMIT 1`; no later-bin coalescing occurs. Postal codes and house
numbers stay text, including leading zeros. Count and NUMERIC SUM cover every
child. Distinct group/carrier queries exclude only NULLs and order by stored
text. No-child parents still return 200 with count 0, null location text/capacity
and empty arrays. Known zero capacity stays numeric zero. SQL SUM ignores NULLs
and remains NULL when no known capacity exists; no source-unit conversion occurs.
The displayed `m³` is still an **unverified source-unit assumption**.

The stored Site coordinate is an arithmetic mean of member-bin coordinates,
including retained out-of-bounds members; it is not a surveyed entrance. The map
uses `[longitude, latitude]`, zoom 15.5, bearing/pitch 0 and `interactive: false`.
MapLibre CSS and a separate Vite-bundled ESM worker are included. The component
updates marker/center on coordinate changes, observes container resize, removes
the marker/map and observer on unmount, and cancels its loading timeout. Required
attribution remains expanded and visible on narrow screens. Configuration,
resource or WebGL errors stay in the map area; map retry creates a new map without
fetching site data. NULL coordinates display `N/A` and skip map initialization.

Use `frontend/.env.example` for native startup in the isolated checkout, as shown
in README. Vite reads `frontend/.env.local` at startup, not the backend's root
`.env`. Exported `VITE_MAP_STYLE_URL` overrides frontend file values. The initial
style is `https://tiles.openfreemap.org/styles/liberty`; another HTTP(S) style URL
can be supplied without editing the component. Missing/invalid configuration has
a Lithuanian error and no hardcoded component fallback. Builds embed the style:

```bash
cd /home/stitas/.local/share/viptop-isolated/bins-ui/frontend
npm ci
VITE_MAP_STYLE_URL=https://tiles.openfreemap.org/styles/liberty npm run build
VIPTOP_API_PROXY_TARGET=http://127.0.0.1:8001 npm run preview -- --host 127.0.0.1 --port 5174 --strictPort
```

Run a native preview only when port 5174 is free and no owned verification
frontend already uses it. Stop only the preview you started when finished.
Changing environment variables on preview does not change a prebuilt bundle.
For the new verification frontend container, set `BINS_UI_MAP_STYLE_URL` before
the dependency-free initial startup above. The temporary override passes it as
`VITE_MAP_STYLE_URL`. Once that container is safely running, this prints only the
public style URL (never its full environment) and exits 1 if missing:

```bash
docker exec viptop-bins-ui-verification-frontend node -e '
const style = process.env.VITE_MAP_STYLE_URL;
if (!style) process.exit(1);
console.log(style);
'
```

Then inspect the new frontend's browser network requests: the style request must
match that value. Do not edit root `.env` or restart any operational service to
change map configuration. For container verification of a different style,
configure it before starting the new frontend. Native checks below used explicit
startup/build environment values and did not create any root/frontend env file.

## Repeatable read-only detail checks

After safe startup and storage identity verification above, select a real site ID
from the list output; do not create fixture rows. The curl command exits nonzero
on transport/non-2xx errors and records the actual returned detail:

```bash
read -rp 'Existing site ID from the separate /sites response: ' BINS_UI_VERIFY_SITE_ID
export BINS_UI_VERIFY_SITE_ID
curl --fail --silent --show-error --max-time 10 \
  "http://127.0.0.1:8001/sites/$BINS_UI_VERIFY_SITE_ID" \
  > "$BINS_UI_RUNTIME_DIR/site-detail.json"
python3 -m json.tool "$BINS_UI_RUNTIME_DIR/site-detail.json"
```

The following command compares the implemented service with ordered raw SQL in
one existing-storage snapshot and reports first-child identity, all-child
aggregates and timing. It runs only in the exactly identified **new backend**,
rolls back its read-only transaction and exits nonzero on any mismatch/failure.
It neither inserts fixtures nor runs migrations/import. A missing requested site
means the selected ID must be checked against current committed storage.

```bash
docker exec -i -e BINS_UI_VERIFY_SITE_ID viptop-bins-ui-verification-backend /app/.venv/bin/python - <<'PY'
import os
from time import perf_counter
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.core.config import Settings
from app.infrastructure.database import create_database_engine
from app.services.sites import get_site, SiteNotFoundError

site_id = int(os.environ['BINS_UI_VERIFY_SITE_ID'])
assert 0 < site_id <= 2**63 - 1
engine = create_database_engine(Settings())
try:
    with Session(engine) as session:
        session.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY'))
        session.execute(text("SET LOCAL statement_timeout = '5s'"))
        session.execute(text("SET LOCAL lock_timeout = '1s'"))
        assert session.scalar(text("SELECT current_setting('transaction_read_only')")) == 'on'
        params = {'id': site_id}
        identity = session.execute(text('SELECT id,address,latitude,longitude FROM sites WHERE id=:id'), params).mappings().one()
        first = session.execute(text('SELECT id,sub_district,street,house_number,postal_code FROM bins WHERE site_id=:id ORDER BY id LIMIT 1'), params).mappings().one_or_none()
        count, capacity = session.execute(text('SELECT count(*),sum(capacity_m3) FROM bins WHERE site_id=:id'), params).one()
        groups = list(session.scalars(text('SELECT DISTINCT object_group FROM bins WHERE site_id=:id AND object_group IS NOT NULL ORDER BY object_group'), params))
        carriers = list(session.scalars(text('SELECT DISTINCT waste_carrier FROM bins WHERE site_id=:id AND waste_carrier IS NOT NULL ORDER BY waste_carrier'), params))
        expected = dict(identity)
        expected.update({field: first[field] if first is not None else None for field in ('sub_district','street','house_number','postal_code')})
        expected.update(bin_count=count, total_capacity_m3=float(capacity) if capacity is not None else None, object_groups=groups, waste_carriers=carriers)
        started = perf_counter()
        actual = get_site(session, site_id)
        elapsed = perf_counter() - started
        assert actual == expected, (actual, expected)
        assert set(actual) == set(expected)  # No nested history/bin fields.
        print('Lowest internal child:', dict(first) if first is not None else None)
        print('Detail agrees with raw SQL:', actual)
        print('Detail service seconds:', round(elapsed, 4))
        # This synthetic ID is above the actual BIGINT identity domain; no writes.
        try:
            get_site(session, 10**40)
        except SiteNotFoundError:
            print('PASS missing parent; existing empty parents remain 200')
        else:
            raise AssertionError('Expected missing parent')
        session.rollback()
except SQLAlchemyError as error:
    raise SystemExit(f'FAIL: detail read ({type(error).__name__}); SQL/credentials omitted.') from None
finally:
    engine.dispose()
PY
```

Compare the separately recorded HTTP detail to these SQL values. Import can
change aggregates between separate snapshots; record such changes and repeat
the reads rather than treating them as a frozen dataset. Check a genuinely
absent positive in-range ID through HTTP for 404, and `/sites/0` and `/sites/abc`
for 422. Check an actual zero-bin parent, a first child's NULL followed by a later
child's known value, text with leading zeros, all-NULL capacity and known zero
only when those scenarios exist. Record their absence or unmet access; no fixture
inserts, even rolled back, are allowed.

## Detail UI procedure and current evidence

On the separate frontend, open `/admin/sites/{id}` directly and refresh. Confirm
the address header, back link, active collection navbar, map and these labels:
`Seniūnija`, `Gatvė`, `Namo numeris`, `Pašto kodas`, `Konteinerių skaičius`,
`Naudotojai`, `Bendra talpa`, `Atliekų vežėjas`. Compare each value with the real
detail/SQL result. Check comma-separated distinct lists, `N/A` for NULL/empty
arrays and zero as a meaningful value. Verify street names and attribution at
desktop/320px, then attempt wheel, drag, pinch, rotation and keyboard manipulation;
the view must stay fixed. Missing parents retain back navigation; detail failures
have their own retry. Locally fail external map resources, then retry the map:
statistics must remain usable and the detail API must not be requested again.
Browser-local synthetic responses are allowed for presentation of unavailable
scenarios; label them explicitly and never report them as database observations.

Observed offline/presentation evidence on 2026-10-09:

- `npm install maplibre-gl` and lockfile-based `npm ci` passed, installing MapLibre
  6.13.0. Frontend lint/build and focused Python syntax/Ruff checks passed. Vite
  emitted a separate worker asset. Its normal large-bundle warning remains;
  it is not a failed build. No automated test files were added.
- Offline PostgreSQL compilation and synthetic read results verified ordered
  first-child selection, five focused detail queries, NUMERIC SUM without
  COALESCE, ordered distinct non-NULL text and absence of history joins/ORM trees.
  Synthetic results covered first-child NULLs, postal code `08303`, house `53A`,
  12 children across hypothetical pages, no-child parents and zero/NULL capacity.
- In-process synthetic HTTP checks passed for detail 200, empty-parent 200,
  missing-parent 404, invalid IDs 422, read-only snapshot setup/rollback and generic
  persistence 500. OpenAPI exposed the flat contract and static-route precedence.
  These checks used session doubles and attempted no database connection.
- The in-app Browser was unavailable; standalone Chromium checked the isolated
  preview on port 5174, with **every `/api/**` request intercepted**. Synthetic
  data used site 7, address `Kalvarijų g. 53A`, coordinate `[25.279,54.701]`,
  12 children and capacity 3.6. Address/coordinate correspondence is synthetic;
  none of these values are observed storage records.
- Real external OpenFreeMap Liberty resources loaded using the URL supplied at
  build time. Browser verification used `ignore_https_errors` for the local
  verification context and software WebGL; operator-browser TLS/GPU remains a
  separate live check. Street labels, correct marker center and expanded
  OpenFreeMap/OpenMapTiles/OpenStreetMap attribution were inspected at 1280px and
  320px. Screenshots: `/tmp/bins-ui-detail-desktop.png` and
  `/tmp/bins-ui-detail-mobile.png` (temporary evidence may disappear).
- Synthetic browser checks passed for direct open/refresh, disabled wheel/drag/
  pinch/keyboard manipulation, canvas outside the keyboard tab order, marker
  center after responsive resize, and no horizontal overflow at 320px.
- A browser-local map-resource failure retained statistics. Map retry recovered
  without another detail request. Synthetic detail failure/retry, missing-site
  back navigation, NULL coordinates with no canvas, empty-parent count 0,
  `N/A` fields/arrays and known-zero capacity `0 m³` passed.
- A second native isolated frontend on port 5175 started with explicit empty
  `VITE_MAP_STYLE_URL` and proxy target 8001. Missing configuration displayed its
  own error, kept statistics usable and initialized no canvas. Root `.env` and
  frontend env files were not edited. No existing services were restarted.
- A third native isolated frontend on port 5176 started with OpenFreeMap Bright;
  the browser requested and rendered exactly that style, with no Liberty request.
  This verifies alternate startup configuration independently of the Liberty
  build. Bright emitted provider-style warnings about NULL road-shield filter
  values and a missing `office` sprite; the map rendered and no application error
  occurred. All three native servers were owned temporary verification processes.
- A follow-up check inspected the existing map ref in the synthetic browser:
  center `[25.279,54.701]`, zoom 15.5, bearing/pitch 0 and disabled interaction
  handlers remained unchanged after wheel, drag, right-drag rotation, pinch and
  keyboard input. A screenshot-byte comparison had been inconclusive while
  external tiles rendered; the actual camera/handler inspection resolved that
  uncertainty. Delayed old detail responses could not replace a newer selection;
  switching sites updated the coordinate and leaving details removed canvas and
  marker elements. No application instrumentation was added.
- Final baseline comparison passed for all 136 tracked operational files.
  Unlike the earlier group 2 observation, PIDs 493715, 493931, 678068 and 493638
  are now absent. Current read-only `/proc` metadata shows frontend PID 741444
  in container `fce1c953be94a2a017b9fcfc358c746f905fa670580db31816f2e1910235960b`,
  backend PID 741641 in
  `c916fb19136977b414bc6e0fee70b4c7e9f6345a82fe8a23d3953b6edf5d4d7a`,
  and PostgreSQL PID 741259 in
  `3886bb6ad29548f884211dce4b1f98c708edbba50bd6b3a50788861f73bc5fc9`.
  Importer PID 741891 is in the backend cgroup. Source mount metadata still excludes
  the isolated checkout; ports 5173/8000/5432 have listeners. This does not prove
  importer progress, database health or continuity of the earlier container IDs.
  No operational runtime mutation was issued by this implementation session.
  **Refresh every runtime ID/network through read-only inspection before using
  the earlier startup/baseline examples; their hardcoded preflight IDs are
  historical and must not be reused as current ownership evidence.**
- The three owned native frontend processes on ports 5174–5176 were stopped
  after verification. Documented Bash/Python syntax checks passed without running
  any Docker/database commands. Whitespace and strict OpenSpec validation passed;
  no models, migrations, importer, permanent Compose or automated test files
  were added or changed by this detail increment.

**Unmet live evidence for tasks 3.1, 3.3–3.5:** current-storage first-child and
aggregate comparisons/timing, availability of backend edge-case records, UI using
real detail responses, verified additional container startup/environment/storage
identity and importer progress. Docker API inspection again returned permission
denied, so no additional containers were started. Task 3.2 is complete; the other
four tasks have code/documentation and synthetic checks but remain unchecked
pending these required live checks.

## Child-bin and history contracts

`GET /sites/{site_id}/bins?page=1&page_size=10` returns
`{items: [{id, inventory_number, waste_type, capacity_m3}], total, page, page_size}`.
The parent must exist even for an out-of-range page. Rows filter by `site_id` and
sort by internal `bins.id ASC`; only the requested page's four summary fields are
selected. Sizes 1–100 are valid; default is 10. Capacity is a JSON number or null,
including numeric zero. Existing empty sites return total 0 and empty items.
The independently fetched detail statistics cover all children on every bin page.

`GET /bins/{bin_id}/history?page=1&page_size=20` returns
`{items: [{id, date, was_serviced, non_serviced_reason, fill_level}], total, page,
page_size, successful_service_percentage, unsuccessful_service_percentage}`.
Sizes 1–20 are valid; default/max is 20. Naive ISO dates have no added UTC/offset.
Rows sort by `date DESC, id DESC`. One all-history aggregate counts true/false
statuses independently of LIMIT/OFFSET. Success is rounded to one decimal and
failure is its rounded complement to 100. These describe currently stored
observations, not predictions or proof of complete source coverage. No-history
bins return total 0, empty items and null percentages; genuine 0%/100% survives.

Both endpoints are GET-only, using the dedicated short repeatable-read/read-only
snapshot and local 5s statement/1s lock timeouts. Missing positive parents return
404. Invalid/nonpositive IDs/pages/sizes, child size 101 and history size 21 return
422. Huge positive IDs outside BIGINT return 404 without querying storage; valid
out-of-range pages return correct totals/percentages without overflowing OFFSET.
Persistence failures return sanitized `500 {"detail":"Collection read failed"}`.
Models, migrations, importer and operational startup are unchanged.

## Repeatable child/history reads

Run only after safe new-container startup and existing-storage identity checks
above pass. The current session has not established that startup. Use the **new**
backend on port 8001; never substitute the operational server. Select existing
IDs without inserting fixtures. `curl --fail` exits nonzero for transport/non-2xx
failures. These commands record actual returned records, not browser examples:

```bash
read -rp 'Existing site ID from the separate /sites response: ' BINS_UI_VERIFY_SITE_ID
export BINS_UI_VERIFY_SITE_ID
curl --fail --silent --show-error --max-time 10 \
  "http://127.0.0.1:8001/sites/$BINS_UI_VERIFY_SITE_ID/bins?page=1" \
  > "$BINS_UI_RUNTIME_DIR/site-bins-page.json"
python3 -m json.tool "$BINS_UI_RUNTIME_DIR/site-bins-page.json"
read -rp 'Internal bin ID from that page (not external/inventory ID): ' BINS_UI_VERIFY_BIN_ID
export BINS_UI_VERIFY_BIN_ID
curl --fail --silent --show-error --max-time 10 \
  "http://127.0.0.1:8001/bins/$BINS_UI_VERIFY_BIN_ID/history?page=1" \
  > "$BINS_UI_RUNTIME_DIR/bin-history-page.json"
python3 -m json.tool "$BINS_UI_RUNTIME_DIR/bin-history-page.json"
```

This command compares services with raw SQL in one existing-data snapshot,
reports ordered membership, all-child statistics, all-history percentages,
fill/date/reason records and timings, and exits nonzero on failed reads/mismatch.
It rolls back without writes, migrations or imports. Compare separately recorded
HTTP values with its output; import can change records between requests. Repeat
and record changes instead of claiming cross-request snapshot consistency.

```bash
docker exec -i -e BINS_UI_VERIFY_SITE_ID -e BINS_UI_VERIFY_BIN_ID \
  viptop-bins-ui-verification-backend /app/.venv/bin/python - <<'PY'
import os
from time import perf_counter
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.core.config import Settings
from app.infrastructure.database import create_database_engine
from app.services.sites import get_site, list_bins, SiteNotFoundError
from app.services.bins import get_history, BinNotFoundError

site_id = int(os.environ['BINS_UI_VERIFY_SITE_ID'])
bin_id = int(os.environ['BINS_UI_VERIFY_BIN_ID'])
assert 0 < site_id <= 2**63 - 1 and 0 < bin_id <= 2**63 - 1
engine = create_database_engine(Settings())
try:
    with Session(engine) as session:
        session.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY'))
        session.execute(text("SET LOCAL statement_timeout = '5s'"))
        session.execute(text("SET LOCAL lock_timeout = '1s'"))
        assert session.scalar(text("SELECT current_setting('transaction_read_only')")) == 'on'
        params = {'site': site_id, 'bin': bin_id}
        assert session.scalar(text('SELECT site_id FROM bins WHERE id=:bin'), params) == site_id
        count = session.scalar(text('SELECT count(*) FROM bins WHERE site_id=:site'), params)
        detail = get_site(session, site_id)
        for page in (1, 2, 10**40):
            started = perf_counter()
            result = list_bins(session, site_id, page=page, page_size=10)
            expected = []
            if (page - 1) * 10 < count:
                expected = [dict(r) for r in session.execute(text('SELECT id,inventory_number,waste_type,capacity_m3 FROM bins WHERE site_id=:site ORDER BY id LIMIT 10 OFFSET :offset'), {**params, 'offset': (page - 1) * 10}).mappings()]
                for row in expected:
                    row['capacity_m3'] = float(row['capacity_m3']) if row['capacity_m3'] is not None else None
            assert result == dict(items=expected, total=count, page=page, page_size=10)
            assert get_site(session, site_id) == detail
            print('Observed child page:', result, 'seconds:', round(perf_counter() - started, 4))
        total, successes, failures = session.execute(text('SELECT count(*),count(*) FILTER (WHERE was_serviced),count(*) FILTER (WHERE NOT was_serviced) FROM bin_hist WHERE bin_id=:bin'), params).one()
        assert total == successes + failures
        success = round(100 * successes / total, 1) if total else None
        failure = round(100 - success, 1) if success is not None else None
        for page in (1, 2, 10**40):
            started = perf_counter()
            result = get_history(session, bin_id, page=page, page_size=20)
            expected = [] if (page - 1) * 20 >= total else [dict(r) for r in session.execute(text('SELECT id,date,was_serviced,non_serviced_reason,fill_level FROM bin_hist WHERE bin_id=:bin ORDER BY date DESC,id DESC LIMIT 20 OFFSET :offset'), {**params, 'offset': (page - 1) * 20}).mappings()]
            assert result == dict(items=expected, total=total, page=page, page_size=20, successful_service_percentage=success, unsuccessful_service_percentage=failure)
            print('Observed history page:', result, 'seconds:', round(perf_counter() - started, 4))
            assert all(row['date'].tzinfo is None for row in result['items'])
            assert all(row['fill_level'] in (None, 0, 1, 2, 3) for row in result['items'])
        fills = list(session.execute(text('SELECT fill_level,count(*) FROM bin_hist WHERE bin_id=:bin GROUP BY fill_level ORDER BY fill_level NULLS LAST'), params))
        ties = list(session.execute(text('SELECT date,count(*) FROM bin_hist WHERE bin_id=:bin GROUP BY date HAVING count(*)>1 ORDER BY date DESC LIMIT 5'), params))
        print('Observed fill counts:', fills, 'tied dates:', ties)
        observed = {level for level, _ in fills}
        print('Fill cases absent for this selected bin:', [v for v in (0, 1, 2, 3, None) if v not in observed])
        print('No-history example:', total == 0, 'zero-success example:', total > 0 and successes == 0)
        for service, missing in ((list_bins, SiteNotFoundError), (get_history, BinNotFoundError)):
            try:
                service(session, 10**40, page=1, page_size=10)
            except missing:
                pass
            else:
                raise AssertionError('Expected missing parent')
        session.rollback()
except SQLAlchemyError as error:
    raise SystemExit(f'FAIL: collection read ({type(error).__name__}); SQL/credentials omitted.') from None
finally:
    engine.dispose()
print('PASS: raw SQL agrees with bounded pages and global aggregates')
PY
```

Validate 422 and impossible-ID 404 with GET only; failures exit nonzero:

```bash
python3 - <<'PY'
from urllib.request import urlopen
from urllib.error import HTTPError
from os import environ
base = 'http://127.0.0.1:8001'
site = environ['BINS_UI_VERIFY_SITE_ID']
bin_id = environ['BINS_UI_VERIFY_BIN_ID']
for path, expected in (
    (f'/sites/{site}/bins?page_size=101', 422),
    (f'/bins/{bin_id}/history?page_size=21', 422),
    (f'/bins/{bin_id}/history?page=0', 422),
    (f'/bins/{bin_id}/history?page=abc', 422),
    (f'/sites/{10**40}/bins', 404),
    (f'/bins/{10**40}/history', 404),
):
    try:
        with urlopen(base + path, timeout=10) as response:
            actual = response.status
    except HTTPError as error:
        actual = error.code
    assert actual == expected, (path, actual, expected)
    print(actual, path)
print('PASS: invalid pagination and missing-parent responses')
PY
```

This offline formatter command uses synthetic inputs, needs no server/storage,
and exits nonzero on changed zero/NULL/wall-clock formatting. Run from the isolated
checkout with the project's modern Node version. Browser evidence below also
checks the two timezones:

```bash
cd /home/stitas/.local/share/viptop-isolated/bins-ui
for BINS_UI_VERIFY_TZ in Pacific/Honolulu Asia/Tokyo; do
  TZ="$BINS_UI_VERIFY_TZ" node --experimental-strip-types --input-type=module - <<'JS'
import { formatHistoryDate, formatValue, formatPercentage } from './frontend/src/pages/sites/format.ts';
const date = formatHistoryDate('2026-09-01T08:00:00');
if (date !== '2026-09-01 08:00:00' || formatValue(0) !== '0' || formatValue(null) !== 'N/A' || formatPercentage(0) !== '0%') process.exit(1);
console.log(process.env.TZ, date, [0, 1, 2, 3, null].map(formatValue));
JS
  if [ "$?" -ne 0 ]; then exit 1; fi
done
```

## Child/history UI procedure and evidence (2026-10-09)

On the separate frontend, select a later-page bin by keyboard/touch and compare
its internal ID with the history request; inventory/external IDs are not route
keys. Check inventory number, Lithuanian waste label and capacity; NULLs show
`N/A`. Escape/close restores row focus; reopening/another selection starts page 1.
Bin paging/retry must retain site statistics/map without unrelated detail reads.

Check exactly two bars (`Sėkmingi aptarnavimai`, `Nesėkmingi aptarnavimai`) using
API all-history percentages across pages. No-history replaces bars with an empty
message; known 0% is meaningful. Check raw fill 0–3/NULL, Lithuanian boolean
statuses, preserved source reasons, and stored time components across timezones.
At 320px, scroll history and operate close, Tab/Shift+Tab, Escape, page input and
previous/next. Fail history locally: the summary stays; retry fetches only
history. Close a delayed read and open another bin: the late response must not
replace the new bin's history or percentages.

Observed **offline/synthetic** evidence, separate from storage observations:

- Frontend lint/build and focused Python syntax/Ruff checks passed. The existing
  MapLibre bundle-size warning remains nonfatal.
- Inline session doubles/PostgreSQL compilation verified bounded column sets,
  membership predicates, ASC bins, DESC date/ID history, global count groups,
  page-independent percentages, huge/out-of-range pages, zero/NULL capacity,
  no-history NULL percentages, meaningful 0%/100% and complementary rounding.
  These checks did not execute SQL against a database.
- Synthetic in-process HTTP/OpenAPI checks covered defaults/maximums, GET-only
  routes, 200/404/422, naive date serialization, raw fill 0/false/NULL, snapshot
  setup/rollback and sanitized 500. No database/lifespan startup was used.
- The in-app Browser was unavailable and listed no browsers. Standalone Chromium
  checked the isolated native preview at `127.0.0.1:5174`, with **every `/api/**`
  request intercepted**. Site 7, twelve bins (internal IDs 100–111), 45 attempts
  and 81%/19% are browser-local synthetic responses, not imported observations.
  NULL coordinates avoided map initialization/external map resources.
- Browser checks passed for 10/2 bin pages, later-page IDs, header NULL/zero,
  localized waste labels, Enter activation, focus return/trap, reopening page 1,
  history page 2, exactly two unchanged bars, no-history without bars, 0%/100%,
  fill 0–3/NULL, nullable reasons and both Lithuanian statuses.
- Honolulu and Tokyo browser contexts displayed the identical stored wall clock
  `2026-09-01 08:00:00`. The offline formatter command also passed both timezones.
- Failed history/retry preserved the summary and fetched history only. Closing
  a delayed request then selecting another bin retained the new selection/page.
  Bin failure/retry retained site details. At 320×740px, dialog/close/pagination
  fit the viewport, no horizontal overflow occurred, keyboard focus stayed
  inside the dialog, PageDown scrolled history and closing restored row focus.
- Desktop/mobile screenshots were visually inspected at
  `/tmp/bins-ui-history-desktop.png` and `/tmp/bins-ui-history-mobile.png`.
  Temporary screenshots may disappear. No automated test files were added.

Final runtime/source observation: all 136 tracked operational files still
match their recorded baseline. Frontend PID 741444, backend PID 741641 and
PostgreSQL PID 741259 remain in the previously observed container cgroups;
their readable mount metadata excludes the isolated checkout. Importer PID
741891 is now absent. No inference about import completion/failure or database
health is possible from this observation. No operational runtime mutation was
issued; the owned native preview on port 5174 was stopped. Source remains
isolated pending an explicit later activation after runtime state is established.
Documentation syntax checks passed for 20 Bash blocks/seven embedded Python
commands without running the Docker/database commands. Strict OpenSpec validation,
whitespace and focused backend checks passed.

**Unmet real-storage evidence (4.1 and 4.3):** child membership/page values,
all-child aggregate independence/timing; real history counts/percentages/order/
timing; in-range missing parents; availability of NULL inventory/capacity/reason/
fill, known-zero capacity, fills 0–3, tied dates, empty parents and no-history/
zero-success bins. Docker access remains denied, so no real records were read or
verification containers started. Whether these edge cases exist is **unknown**,
not evidence of absence. The SQL procedure reports absent cases for the selected
bin once access exists; do not insert fixtures to fill coverage gaps. Frontend
4.2/4.4/4.5 and documentation 4.6 are complete; 4.1/4.3 have code and synthetic
checks but stay unchecked until required real reads. No migrations, imports,
fixture writes or operational source/container changes were performed.

## Cleanup only owned containers

First confirm both exact names resolve to the new IDs recorded at startup, project `viptop-bins-ui-verification` and owner label `bins-ui`:

```bash
docker inspect --format '{{.Id}} {{.Name}} {{index .Config.Labels "com.docker.compose.project"}} {{index .Config.Labels "viptop.verification.owner"}}' \
  viptop-bins-ui-verification-backend viptop-bins-ui-verification-frontend
```

After those checks, stop/remove only these additional application containers, without `--volumes`:

```bash
docker stop viptop-bins-ui-verification-frontend viptop-bins-ui-verification-backend
docker rm viptop-bins-ui-verification-frontend viptop-bins-ui-verification-backend
unset BINS_UI_DATABASE_URL
```

Leave PostgreSQL, operational applications/import, their volumes and all shared networks intact. No cleanup was needed or performed in the recorded session because no additional containers were started.
