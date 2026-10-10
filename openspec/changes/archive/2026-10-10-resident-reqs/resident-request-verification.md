# Resident request verification

Use disposable PostgreSQL storage and clearly synthetic records for the write,
failure, downgrade, and deletion checks below. Commands exit nonzero on SQL or
migration failure. `podman` can be replaced by `docker` where available.

## Disposable database and additive migration

From the repository root:

```bash
podman run -d --name viptop-resident-reqs-verify-db \
  -p 127.0.0.1:55433:5432 \
  -e POSTGRES_USER=viptop -e POSTGRES_PASSWORD=viptop \
  -e POSTGRES_DB=viptop_resident_verify docker.io/library/postgres:17-alpine
podman exec viptop-resident-reqs-verify-db pg_isready -U viptop
```

In `backend/`, use only the disposable connection:

```bash
export DATABASE_URL=postgresql+psycopg://viptop:viptop@127.0.0.1:55433/viptop_resident_verify
export BIN_SYNC_HTTP_TIMEOUT_SECONDS=1
export VASA_TILE_URL_TEMPLATE='https://127.0.0.1:1/{z}/{x}/{y}'
export VASA_BIN_URL_TEMPLATE='https://127.0.0.1:1/{external_id}'
export VASA_HISTORY_URL_TEMPLATE='https://127.0.0.1:1/{external_id}'
uv sync --locked
uv run alembic upgrade 0004
```

Populate the empty revision-0004 verification database. These internal IDs are
deterministic only in this fresh synthetic database:

```bash
podman exec -i viptop-resident-reqs-verify-db \
  psql -v ON_ERROR_STOP=1 -U viptop -d viptop_resident_verify <<'SQL'
INSERT INTO sites(site_key,address,latitude,longitude)
VALUES ('address:synthetic resident site','Synthetic resident site',54.6872,25.2797);
INSERT INTO bins(site_id,external_id,inventory_number,waste_type,latitude,longitude)
VALUES (1,135353,'00123','Glass waste',54.6872,25.2797),
       (1,135354,NULL,'Mixed municipal waste',54.6872,25.2797),
       (1,135355,repeat('Ilgas numeris ',20),'Paper/plastic waste',54.6872,25.2797);
INSERT INTO bin_hist(bin_id,date,was_serviced,fill_level)
VALUES (1,'2026-10-08 08:00:00',true,2);
INSERT INTO trucks(name,max_bins_per_trip,available)
VALUES ('Synthetic resident verification truck',35,true);
INSERT INTO vasa_import_runs(scope_key,coverage,phase)
VALUES ('resident-synthetic','{}','tiles');
INSERT INTO vasa_import_progress(run_id,kind,work_key,complete,details)
VALUES (1,'seen','135353',true,'{}');
SQL
uv run alembic upgrade head
uv run alembic upgrade head
uv run alembic check
podman exec viptop-resident-reqs-verify-db \
  psql -v ON_ERROR_STOP=1 -U viptop -d viptop_resident_verify -c '\d resident_requests'
```

Expect revision `0005`, no schema drift, and exactly required columns `id`
(generated BIGINT), `bin_id` (BIGINT cascading FK), and `timestamp` (TIMESTAMP
WITHOUT TIME ZONE with explicit Europe/Vilnius default). Compare ordered row
JSON before/after upgrade for sites, bins, bin history, trucks, and both import
bookkeeping tables: all identities and values must match. In disposable storage,
also run `uv run alembic downgrade 0004` then `uv run alembic upgrade head` and
repeat the comparison. This drops only resident requests. Do not downgrade
below `0004`, whose historical replacement cannot restore legacy data.

For a fresh-schema check, create a second disposable database:

```bash
podman exec viptop-resident-reqs-verify-db createdb -U viptop viptop_resident_fresh
DATABASE_URL=postgresql+psycopg://viptop:viptop@127.0.0.1:55433/viptop_resident_fresh \
  uv run alembic upgrade head
DATABASE_URL=postgresql+psycopg://viptop:viptop@127.0.0.1:55433/viptop_resident_fresh \
  uv run alembic check
```

Neither schema setup nor startup should fetch VASA or run registry cleanup.

## Storage clock, constraints, and cascade

```bash
podman exec -i viptop-resident-reqs-verify-db \
  psql -v ON_ERROR_STOP=1 -U viptop -d viptop_resident_verify <<'SQL'
SET TIME ZONE 'UTC';
INSERT INTO resident_requests(bin_id) VALUES (1) RETURNING *;
SELECT statement_timestamp() AT TIME ZONE 'Europe/Vilnius' AS vilnius_now;
SELECT '2026-01-15 12:00:00+00'::timestamptz AT TIME ZONE 'Europe/Vilnius' AS winter,
       '2026-07-15 12:00:00+00'::timestamptz AT TIME ZONE 'Europe/Vilnius' AS summer;
INSERT INTO resident_requests(bin_id,timestamp)
VALUES (1,'2026-10-09 15:30:00'),(1,'2026-10-09 15:30:00');
INSERT INTO resident_requests(bin_id) VALUES (2),(3);
BEGIN;
DELETE FROM bins WHERE id=2;
SELECT count(*) AS removed_child_count FROM resident_requests WHERE bin_id=2;
ROLLBACK;
SELECT count(*) AS restored_child_count FROM resident_requests WHERE bin_id=2;
BEGIN;
DELETE FROM bins WHERE id=3;
SELECT count(*) AS removed_child_count FROM resident_requests WHERE bin_id=3;
ROLLBACK;
SELECT bin_id,count(*) FROM resident_requests GROUP BY bin_id ORDER BY bin_id;
SQL
```

Expect generated local naive time even with the UTC session; winter conversion
is 14:00 and summer is 15:00. Equal bin/time pairs remain separate records.
Deleting a parent makes its child count zero inside the transaction; rollback
restores the parent and requests. Other bins' requests survive. To check committed
cascade, delete a separate synthetic parent permanently and confirm its requests
are absent after reconnecting. Preserve bins 1–3 for the page checks.

Run each invalid insert independently and expect a nonzero command exit:

```bash
podman exec viptop-resident-reqs-verify-db psql -v ON_ERROR_STOP=1 -U viptop \
  -d viptop_resident_verify -c 'INSERT INTO resident_requests(bin_id) VALUES (NULL)'
podman exec viptop-resident-reqs-verify-db psql -v ON_ERROR_STOP=1 -U viptop \
  -d viptop_resident_verify -c 'INSERT INTO resident_requests(bin_id) VALUES (9223372036854775807)'
podman exec viptop-resident-reqs-verify-db psql -v ON_ERROR_STOP=1 -U viptop \
  -d viptop_resident_verify -c 'INSERT INTO resident_requests(bin_id,timestamp) VALUES (1,NULL)'
```

Record saved IDs/timestamps, restart the verification backend, and compare the
rows again. Updating a synthetic bin's inventory number or site membership must
preserve its request references and times. Counts are verification queries only;
this feature does not expose analytical aggregates.

## HTTP API and persistence failure

Start the verification backend from `backend/` with the disposable environment
above (port 58001 avoids existing application services):

```bash
sh start.sh uv run uvicorn app.main:app --host 127.0.0.1 --port 58001
```

In another terminal:

```bash
curl --fail-with-body http://127.0.0.1:58001/bins/1
curl --fail-with-body http://127.0.0.1:58001/bins/2
curl --fail-with-body -i -X POST http://127.0.0.1:58001/bins/1/resident-requests
curl --fail-with-body -i -X POST http://127.0.0.1:58001/bins/1/resident-requests
podman exec viptop-resident-reqs-verify-db psql -v ON_ERROR_STOP=1 -U viptop \
  -d viptop_resident_verify -c 'SELECT id,bin_id,timestamp FROM resident_requests ORDER BY id'
```

GET returns exactly `id`, `address`, `inventory_number`, `waste_type`,
`latitude`, `longitude`, `latest_service`; bin 2 has a null inventory number. `address` is the linked
site address; latitude/longitude belong to the bin, even when site averages
differ. `latest_service` contains only `date` and `was_serviced` from the
latest row ordered by date and ID descending, or null without history. Confirm this by changing only synthetic site coordinates and rereading
the bin. POST requires no body, returns 201 with `{"success":true}`,
and adds one committed row per independent call. Inspect `/openapi.json` or
`/docs` to confirm the contracts and lack of a request-body timestamp.
`Bin.id` 1 differs from source ID 135353: GET/POST using the latter returns 404.
For both routes, absent positive IDs and 9223372036854775808 return 404;
0, -1, noninteger text, and 1.5 return 422. Each error must leave counts unchanged.
Stop and restart this verification backend through `start.sh`; saved requests
and history must survive repeated schema preparation.

Use a temporary trigger only in disposable storage to exercise persistence
failure. Remove it immediately after the failing API call:

```bash
podman exec -i viptop-resident-reqs-verify-db psql -v ON_ERROR_STOP=1 \
  -U viptop -d viptop_resident_verify <<'SQL'
CREATE FUNCTION resident_verify_fail() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'synthetic persistence failure'; END $$;
CREATE TRIGGER resident_verify_fail BEFORE INSERT ON resident_requests
FOR EACH ROW EXECUTE FUNCTION resident_verify_fail();
SQL
curl -i -X POST http://127.0.0.1:58001/bins/1/resident-requests
podman exec -i viptop-resident-reqs-verify-db psql -v ON_ERROR_STOP=1 \
  -U viptop -d viptop_resident_verify <<'SQL'
DROP TRIGGER resident_verify_fail ON resident_requests;
DROP FUNCTION resident_verify_fail();
SQL
```

Expect generic 500 `{"detail":"Resident request failed"}`, no SQL/exception
details, and no additional row. A subsequent POST must succeed. Apply the same
failure during the browser flow to verify the exact error toast and re-enabled
button. A failure at COMMIT must also roll back: the temporary trigger can be
changed to an `AFTER INSERT`, `DEFERRABLE INITIALLY DEFERRED` constraint trigger
to exercise that case before removing it.

For the deletion race, create a separate synthetic bin and briefly delay its
resident-request insert with a temporary BEFORE INSERT trigger (`pg_sleep(0.5)`)
in disposable storage. Start its POST and then delete that bin in a second
transaction while the insert is pending. The parent key-share lock should make
deletion wait for submission to commit; the POST succeeds, then deletion
cascades the request. If deletion commits first, POST returns 404. Neither
ordering can leave a detached request. Remove the delay trigger/function and
confirm later calls work normally. Also verify lock contention exceeding the
one-second lock wait returns a generic failure and leaves no new request.

## Mobile and browser walkthrough

From `frontend/`, run a separate frontend pointing at the verification backend:

```bash
VITE_MAP_STYLE_URL=https://tiles.openfreemap.org/styles/liberty \
  VIPTOP_API_PROXY_TARGET=http://127.0.0.1:58001 \
  npm run dev -- --host 127.0.0.1 --port 55173 --strictPort
```

1. Open `http://127.0.0.1:55173/resident-request/1` directly, then refresh it.
   Expect no admin navbar/layout or role chooser. Read the exact title
   `Siųsti šiukšlių išvežimo prašymą`, a compact map marking the physical bin
   beneath it, `Synthetic resident site` under `Adresas` as the first field,
   inventory `00123` under `Konteinerio numeris`,
   and `Stiklo atliekos` under `Atliekų tipas`. Bin 2 displays `N/A` and
   `Mišrios komunalinės atliekos`; bin 3 exercises long text and
   `Popieriaus ir plastiko atliekos`. Try dragging, wheel/double-click zoom,
   pinch/touch movement, and keyboard zoom: the map must stay fixed and have no
   zoom controls. Block the map style/tiles and reload: fields and `Siųsti`
   remain usable despite the map error.
2. At 320×640, 390×844, and desktop width, confirm no horizontal overflow,
   wrapping long values, a centred narrow desktop column, and a full-width
   bottom-positioned button at least 48px high. Test keyboard Tab/Enter and
   visible focus. Loading shows `Kraunama…`; status feedback and toast errors
   must be understandable without relying on colour or imagery.
3. Throttle the POST and rapidly press `Siųsti`. The pending action must be
   disabled and send one POST. After success, expect a centred large solid green
   circle containing a white checkmark, `Jau vykstame pas Jus` underneath, and
   the specified GIF below the text fitting the column. The original title,
   map, address, bin fields, and submit action must all disappear. Read the SQL row to
   confirm persistence. Refreshing restores the action but creates no row.
4. The image URL must exactly match:
   `https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExbzBjbWJnMWNtZXdiYnBpbGZiNTV5NWFydGcyenUzc3N0bmkxMGplMyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/xsFjLwT7NPfH2/giphy.gif`.
   Block media2.giphy.com, submit again after a page refresh, and confirm the
   checkmark/text remain visible without a broken-image placeholder or submit
   action. The GIF is decorative; textual feedback conveys success.
5. Open a missing ID, zero, negative ID, noninteger ID, and positive BIGINT
   overflow. Expect `Konteineris nerastas` without a request form. Block the bin
   GET with a network failure or 500: expect the supplied generic error plus
   `Bandyti dar kartą`. Unblock and retry; it must only read, not submit.
6. Force a POST failure using the disposable database trigger above or browser
   request blocking. Expect the toast `Kažkas nepavyko. Bandykite dar kartą.`,
   retained bin details, a re-enabled action, and no confirmation state. Restore
   the API and press again; it must successfully commit. No POST auto-retry is
   allowed.
7. Hold a GET or POST response for bin 1 and change the client-side route to
   bin 2 before it resolves. The new bin must show its own details, and the
   old response must not replace them or mark bin 2 successful. A POST already
   received by the server may still commit for its original bin.
8. For BIGINT path precision, insert an explicitly synthetic parent using
   `OVERRIDING SYSTEM VALUE` with internal ID `9007199254740993`, then open its
   URL and submit. Browser Network must show that exact ID in both paths;
   SQL must attach the request to that exact bin. Remove only this fixture
   after checking; database cascade removes its reports.
9. Verify `/admin/sites`, the site's bin list/history, and `/admin/trucks`
   remain usable against synthetic storage. Resident submissions must not
   change bin history or generate derived counts, fill, routes, or predictions.

Run the normal checks from their directories:

```bash
# frontend/
npm run build
npm run lint
# backend/, using the disposable DATABASE_URL
uv run alembic check
# repository root
openspec validate resident-reqs --strict
git diff --check
```

## Verification evidence — 9 October 2026

- PostgreSQL 17 disposable instance on 55433: populated `0004` upgrade,
  repeat upgrades, `0005`-only downgrade/re-upgrade, and fresh migration passed.
  Ordered row snapshots of sites, bins, history, trucks, import runs, and
  import progress were identical across additive/rollback preparation.
  `alembic check` found no schema drift.
- Storage: exactly three required columns; UTC-session default returned
  Europe/Vilnius naive local time; winter/summer conversions, required values,
  nonexistent parent rejection, equal-time distinct records, direct cascade,
  rollback restoration, surviving-bin records, ORM relationships, and metadata
  update retention passed. Saved reports survived an actual backend restart.
- HTTP: minimal GET/OpenAPI response, null values, internal/source distinction,
  404/422/overflow, bodyless 201 and committed row count, independent repeated
  POSTs, insert failure, deferred COMMIT failure, and bounded lock timeout
  passed. Concurrent parent deletion waited for the short submission
  transaction and then cascaded without detached rows. Verification triggers
  were removed afterward; history remained unchanged.
- Local Chromium with the real React/Vite/FastAPI/PostgreSQL flow: direct open
  and refresh, NULL display, missing/invalid IDs, GET failure/retry, single POST
  on rapid taps, exact error toast and successful retry, late GET/POST result
  isolation, keyboard focus/submission, precise large-ID path, and no horizontal
  overflow at 320/390/1280 widths passed. The phone button measured 272×48px at
  320px width. No browser runtime errors were observed.
- The exact supplied GIF returned HTTP 200 and was downloaded for deterministic
  image-layout verification; the same image was displayed at 272×272px within
  the 320px page. Blocking the GIF preserved textual success and removed the
  broken image while keeping the submit action absent.
- Frontend build and lint passed. Build reported its existing large-bundle
  advisory; no unrelated code splitting changes were made.
- Final integration also opened the synthetic admin site list, bin/history
  dialog, and truck list successfully. The existing local database was upgraded
  additively to `0005`; its 21,951 bins were retained, schema consistency passed,
  and the new resident table remained empty. The existing frontend/backend on
  ports 5173/8000 loaded `/resident-request/3` at phone width without navigation
  or overflow. No synthetic resident reports were submitted to that database.

Temporary screenshots and browser tooling used for these checks live outside
the repository. These results use labelled synthetic data, not claims about
real resident reports or prediction quality.

## Presentation revision verification — 9 October 2026

- The expanded GET/OpenAPI contract passed against both the existing API and
  disposable PostgreSQL storage: linked-site address, physical-bin coordinates
  distinct from site averages, nullable inventory, and existing 404/422 rules.
- The revised page loaded real map tiles. Field order was address, inventory,
  waste type. The map had no zoom controls or keyboard focus; mouse drag,
  wheel, double-click, and keyboard attempts left its marker position unchanged.
- Layout checks passed at 320×640, 390×844, and 1280×900 without horizontal
  overflow. The 320px submit button measured 272×48px. Ready and success
  screenshots were visually inspected.
- A real POST committed in disposable storage and replaced the original title,
  map, fields, and button with the supplied GIF, exact `Jau vykstame pas Jus`
  text, and a 112px solid green circle containing a white checkmark.
- Frontend build and lint passed after the functional edits; the subsequent
  code edit only aligned JSX indentation. Strict OpenSpec validation passed.
- Source review confirmed the existing submission error/retry guard remains
  intact, map errors do not gate submission, and GIF failure hides only the
  image while keeping the confirmation.
- Additional live touch/pixel comparison and forced-failure browser checks
  were interrupted and are not claimed as passed. They remain available in
  the manual walkthrough. Further browser/build runs were avoided following
  the user's request to protect their computer's resources. The user subsequently confirmed they independently verified the feature
  and instructed completion of task 5.2 and spec sync/archive on 9 October
  2026. Task 5.2 is closed based on that user verification, rather than an
  additional agent browser run.

## Latest service card verification

Use the existing synthetic history for bin 1: the card must show
`Paskutinis aptarnavimas atliktas` and `2026-10-08` (no time), centred in the
space between the fields and `Siųsti`, with a pale translucent light-blue
background and information icon. Bin 2, without
history, must have no card or empty placeholder. In disposable storage, add an
older record with a higher ID and a newer failed attempt: selection follows
date first, not insertion ID. The same exact label is used for the latest
entry regardless of its status, as requested.
Equal-date records use the higher ID. Other bins’ histories must not affect
selection. Changing the browser timezone must not change the displayed date.
The card must disappear along with the fields after submission succeeds.

Executed checks passed with in-memory SQL fixtures: newest date rather than
insertion order, deterministic same-date ID selection, other-bin isolation,
newest failed visit, missing history, timezone-free JSON, and missing/overflow
IDs. Lightweight syntax and server-rendered component checks passed for the
blue Info card, its position after the fields and before the button, both
labels, timestamp display under a different device timezone, and absence
without history or after success. These checks did not start a browser,
containers, or a production bundle build. Live
mobile visual checks remain a manual walkthrough to respect the user's
resource constraint.

Card styling revision: lightweight syntax/server-render checks passed for the
centred growing flex area, translucent blue background, exact
`Paskutinis aptarnavimas atliktas` label, date-only text and semantic time value,
unchanged date under a different device timezone, and absence without history
or after success. This revision uses the same fixed label for both history
statuses, superseding the earlier two-label presentation. No browser or full
build was launched; visual centring remains part of the manual walkthrough.

## Vilnius logo verification

The logo is a bundled application asset. For a repeatable walkthrough, use the
synthetic bin fixtures above or controlled browser responses; perform submission
checks only against isolated storage or intercepted responses.

1. Open `/` at desktop and 320px widths. Confirm the full red Vilnius logo is
   centered near the top, above VipTop and role selection. The administrator
   action still opens `/admin/trucks`; the driver action remains disabled.
2. Open trucks, sites, and a site-detail route at desktop, 640px, and 320px
   widths. Confirm the compact city logo sits at the right of the shared
   navbar with VipTop on the left, and both branding home links return to `/`. At 320px, open the menu,
   select a link, and reopen/close with Escape; confirm focus returns to the
   toggle and both identities remain visible.
3. Open `/resident-request/{bin_id}` directly and refresh. Confirm the logo is
   centered above the title during loading, ready, failed lookup, missing or
   invalid bin, pending submission, and failed submission states. Read retry
   and submit retry remain usable. Success replaces the logo and all form
   content with the existing confirmation; reload shows the logo again.
4. Check desktop, 320×640, and a short 320×480 viewport, with long addresses
   and inventory numbers, and with/without service history. Confirm there is
   no horizontal overflow, the full image has its original proportions and
   transparent background, and the 48px submit button is reachable by scrolling
   with bottom safe-area spacing. Inspect the accessibility tree for
   `Vilniaus logotipas` before the page heading.
5. Run `npm run build` and `npm run lint` in `frontend/`, then serve the build
   with `npm run preview`. Open and refresh `/`, an admin deep link, and a
   resident deep link. Confirm the logo loads from a bundled `/assets/` URL,
   without access to the original Downloads file or a third-party image host.

Executed on 10 October 2026 for `add-vilnius-logo`: all placements, the navbar
home links and mobile menu/focus behavior, resident loading/error/not-found/
pending/failure/success/reload states, and desktop/320px layouts passed local
Chromium checks. Long values and service-card presence/absence fit at
1280×900, 320×640, and 320×480; scrolling reached the full 48px action.
The accessibility tree exposed the Lithuanian image description. Screenshots
of entry, navbar, resident form, long-value layout, and success were visually
inspected. All API responses and submission outcomes were intercepted in the
browser; no reports were written to real storage. Map configuration was absent
on these verification servers, so the existing map-unavailable placeholder was
verified as usable; live map interactions were not rechecked.

Frontend build and lint passed. Build output included the existing large-chunk
warning. Production preview direct navigation and refresh passed for all three
placements, and the served logo bytes matched the copied source asset. The
in-app browser was unavailable; verification used standalone local Chromium
with temporary checks outside the repository. Existing application services
and data were left running.

Navbar placement revision on 10 October 2026: the Vilnius logo was moved to
the far right, with VipTop on the left. Packaged-build checks passed on trucks,
sites, and site-detail routes at 1280px, 640px, and 320px widths. The logo's
right edge aligned with the navbar's inner right boundary in both mobile menu
states. Both home links, menu selection, Escape, focus restoration, and
horizontal-overflow checks passed. Desktop and open-mobile-menu screenshots
were visually inspected. Build, lint, and bundled-asset direct-route/refresh
checks also passed.

## Cleanup and feature rollback

Stop the separate verification frontend/backend processes. Remove only the
container created for this procedure when it is no longer needed:

```bash
podman rm -f viptop-resident-reqs-verify-db
```

For a feature rollback, first stop serving the resident route/endpoints and
export requests if they are needed, then downgrade only `0005` to `0004`.
That removes this feature's request table and records without touching the
existing collection schema. It does not reverse historical revision `0004`.
