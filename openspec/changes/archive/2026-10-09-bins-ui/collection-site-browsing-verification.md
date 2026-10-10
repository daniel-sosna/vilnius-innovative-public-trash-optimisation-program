# Collection browsing verification

## Runtime after import (2026-10-09)

The user confirmed import is over and authorized the main checkout and real
`docker-compose.yml`. Implementation was transferred from the isolated checkout;
the repository/isolated/temp verification Compose overrides and temporary-path
pointers were deleted. The isolated clone remains a historical implementation
copy, not the startup target. Earlier isolated-runtime restrictions no longer
apply to this user-authorized activation. Database writes, fixture inserts,
resets and import reruns remain outside the read-only verification procedure.

Run from the repository root, with the existing `.env` and database:

```bash
docker compose config --quiet
docker compose build backend frontend
docker compose run --rm --no-deps frontend npm ci
docker compose up -d --no-deps backend frontend
docker compose ps
docker compose logs --tail=50 backend frontend
```

The frontend dependency refresh installs MapLibre into the existing named volume.
PostgreSQL and `postgres_data` are retained. Normal backend startup runs its
existing Alembic upgrade check; collection browsing adds no revision and startup
performs no import. Frontend: `http://localhost:5173/admin/sites`. OpenAPI:
`http://localhost:8000/docs`. Compose passes `VITE_MAP_STYLE_URL` with the default
OpenFreeMap Liberty style; root `.env`/shell values can override it. A native
frontend instead reads `frontend/.env.local`; packaged builds embed the URL at
build time. See README for native commands.

## Completion evidence (2026-10-09)

The user reported completing verification themselves and authorized closing
verification-only remaining tasks. All 27 `bins-ui` tasks are complete on the
basis of implemented behavior, the agent checks below and that user verification.
The user did not supply individual SQL results, query timings or runtime logs;
this document does not invent those measurements.

Agent-run frontend lint/build, focused backend syntax/lint, strict OpenSpec
validation and whitespace checks passed. Docker API access was denied in the
agent session; image builds/container launch and real-storage SQL checks were
not performed by the agent. No runtime startup or database mutation was issued
by this activation. Earlier synthetic checks are
[recorded separately](collection-site-browsing-verification-history.md), and UI
refinement checks are recorded below. They remain synthetic evidence; the
remaining live verification is accepted from the user's report.

The commands below remain available for repeating the checks against the main
Compose application and existing database.

Prepare an output directory for the GET/read-only commands below (no Compose
files are created):

```bash
export BINS_UI_RUNTIME_DIR="$(mktemp -d /tmp/viptop-browsing-checks-XXXXXX)"
```

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

## Repeatable HTTP checks

Run after the main Compose applications are healthy. These GET commands target
the real backend on port 8000. Curl exits nonzero for transport errors or non-2xx responses; response
files retain actual returned values for inspection.

```bash
curl --fail --silent --show-error --max-time 10 \
  http://127.0.0.1:8000/sites > "$BINS_UI_RUNTIME_DIR/sites-page.json"
curl --fail --silent --show-error --max-time 10 \
  'http://127.0.0.1:8000/sites?page=2&page_size=7' > "$BINS_UI_RUNTIME_DIR/sites-custom-page.json"
curl --fail --silent --show-error --max-time 10 \
  http://127.0.0.1:8000/sites/stats > "$BINS_UI_RUNTIME_DIR/sites-stats.json"
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

base = 'http://127.0.0.1:8000'
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

Use the real Compose backend service. All SQL below runs in one
read-only snapshot with finite timeouts; failures exit nonzero with a sanitized
error. It prints aggregate values, ordered pages, grouped page-bin counts,
literal-match totals, and milliseconds per query. Record outputs and timestamps;
do not assert cross-request count equality while import is committing.

```bash
docker compose exec -T backend /app/.venv/bin/python - <<'PY'
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


## Repeatable read-only detail checks

After the main Compose startup above, select a real site ID
from the list output; do not create fixture rows. The curl command exits nonzero
on transport/non-2xx errors and records the actual returned detail:

```bash
read -rp 'Existing site ID from the separate /sites response: ' BINS_UI_VERIFY_SITE_ID
export BINS_UI_VERIFY_SITE_ID
curl --fail --silent --show-error --max-time 10 \
  "http://127.0.0.1:8000/sites/$BINS_UI_VERIFY_SITE_ID" \
  > "$BINS_UI_RUNTIME_DIR/site-detail.json"
python3 -m json.tool "$BINS_UI_RUNTIME_DIR/site-detail.json"
```

The following command compares the implemented service with ordered raw SQL in
one existing-storage snapshot and reports first-child identity, all-child
aggregates and timing. It runs in the real Compose backend,
rolls back its read-only transaction and exits nonzero on any mismatch/failure.
It neither inserts fixtures nor runs migrations/import. A missing requested site
means the selected ID must be checked against current committed storage.

```bash
docker compose exec -T -e BINS_UI_VERIFY_SITE_ID backend /app/.venv/bin/python - <<'PY'
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

Run after the main Compose applications are healthy. The agent has not verified
that startup. Use the real backend on port 8000. Select existing
IDs without inserting fixtures. `curl --fail` exits nonzero for transport/non-2xx
failures. These commands record actual returned records, not browser examples:

```bash
read -rp 'Existing site ID from the separate /sites response: ' BINS_UI_VERIFY_SITE_ID
export BINS_UI_VERIFY_SITE_ID
curl --fail --silent --show-error --max-time 10 \
  "http://127.0.0.1:8000/sites/$BINS_UI_VERIFY_SITE_ID/bins?page=1" \
  > "$BINS_UI_RUNTIME_DIR/site-bins-page.json"
python3 -m json.tool "$BINS_UI_RUNTIME_DIR/site-bins-page.json"
read -rp 'Internal bin ID from that page (not external/inventory ID): ' BINS_UI_VERIFY_BIN_ID
export BINS_UI_VERIFY_BIN_ID
curl --fail --silent --show-error --max-time 10 \
  "http://127.0.0.1:8000/bins/$BINS_UI_VERIFY_BIN_ID/history?page=1" \
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
docker compose exec -T -e BINS_UI_VERIFY_SITE_ID -e BINS_UI_VERIFY_BIN_ID \
  backend /app/.venv/bin/python - <<'PY'
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
base = 'http://127.0.0.1:8000'
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
and exits nonzero on changed zero/NULL/wall-clock formatting. Run from the main
checkout with the project's modern Node version. Browser evidence below also
checks the two timezones:

```bash
cd /home/stitas/Projects/vilnius-innovative-public-trash-optimisation-program
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

## UI checks

Open `/admin/sites`, search/page, then open details and a later-page bin. Compare
API values with the read-only SQL output above. Check map attribution/location,
independent retry, NULL/zero/empty states, only the all-history successful-service percentage bar,
raw fill 0–3, naive wall-clock times, history paging, Escape/focus restoration,
closing/switching during delayed reads, and navigation/scrolling at 320px. Record
which scenarios real records cover; use labeled browser-local synthetic responses
for absent scenarios without inserting fixtures. Preserve the distinction between
live results and earlier synthetic evidence in the linked historical document.

## Requested UI refinements (2026-10-09)

Implemented the container totals/legend beside the donut and green glass
(#15803d), blue paper/plastic (#2563eb), brown mixed waste (#92400e). The shared
pagination control hides for unknown totals, empty and single-page results across
sites/bins/history/Trucks. The history dialog is capped at 1024px with viewport
margins; each attempt has four fields in one row, with horizontal scrolling on
small screens and vertical scrolling for long pages. Its pagination wrapper also
hides for single-page results. The site map enables pan/zoom and localized zoom
buttons. The averaged-coordinate sentence was removed from the UI; the coordinate
meaning remains in README/data documentation.

Frontend lint/build and strict OpenSpec/whitespace checks passed. In-app Browser
was unavailable; standalone Chromium checked the main checkout's owned preview
on port 5174. Every API request was intercepted with browser-local synthetic
responses, and the configured map style URL was intercepted with a local synthetic
style. No real-storage or provider-resource claim is made from these checks.

Browser checks passed for the desktop/mobile donut row and exact SVG/legend
colors; unknown/zero/single/multiple page pagination thresholds across all four
lists; 1024px dialog and four aligned fields per row; 320px dialog margins,
horizontal/vertical history scrolling, focus restoration and multi-page controls;
removed sentence; actual MapLibre drag, wheel, keyboard and zoom-button interaction;
and visible mobile zoom controls/attribution. Desktop/mobile screenshots were
inspected at `/tmp/bins-ui-refined-overview.png`,
`/tmp/bins-ui-refined-overview-mobile.png`,
`/tmp/bins-ui-refined-history-desktop.png`,
`/tmp/bins-ui-refined-history-mobile.png` and
`/tmp/bins-ui-refined-map-mobile.png`. Temporary artifacts may disappear.
No automated test files, backend changes, database writes or migrations were
added. The owned preview was stopped after verification. Earlier historical
noninteractive-map evidence describes the previous version.

The subsequent user-requested dialog adjustment keeps only `Sėkmingi aptarnavimai`
and removes the unsuccessful-service percentage display. The no-history state
and history records retain their existing behavior. Frontend lint/build and
strict OpenSpec validation verify this focused display change.

The subsequent bin-list alignment fix gives the desktop capacity column a fixed
width. Following the user's volume-alignment request, capacity values are also
left-aligned. Waste-type labels and capacity values each share a consistent
starting position regardless of capacity text length. The stacked mobile
layout is retained. Frontend lint/build passed for this adjustment; no new
browser verification is claimed.
