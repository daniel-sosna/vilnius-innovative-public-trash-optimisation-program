# Manual truck-management verification

Use disposable PostgreSQL storage and explicitly synthetic records. Do not run fixture inserts, downgrades, triggers or cleanup against operational storage. No automated test files are required.

## Disposable database and migration

The examples use a standalone database on port 55432. Use `podman` in place of `docker` if that is the available local engine. Create only resources you own:

```bash
docker run -d --name viptop-truck-ui-db -p 127.0.0.1:55432:5432 \
  -e POSTGRES_USER=viptop -e POSTGRES_PASSWORD=viptop \
  -e POSTGRES_DB=viptop_truck_verify postgres:17-alpine
```

From `backend/`, use these disposable settings. The unreachable VASA URLs makes accidental source access visible; migrations and truck requests must not contact it.

```bash
export DATABASE_URL=postgresql+psycopg://viptop:viptop@127.0.0.1:55432/viptop_truck_verify
export VASA_TILE_URL_TEMPLATE='https://127.0.0.1:1/{z}/{x}/{y}'
export VASA_BIN_URL_TEMPLATE='https://127.0.0.1:1/{external_id}'
export VASA_HISTORY_URL_TEMPLATE='https://127.0.0.1:1/{external_id}'
export BIN_SYNC_HTTP_TIMEOUT_SECONDS=1
uv sync --locked
uv run alembic upgrade head
```

At the repository root, create a fleet spanning two pages and one collection-history chain:

```bash
docker exec -i viptop-truck-ui-db psql -v ON_ERROR_STOP=1 -U viptop -d viptop_truck_verify <<'SQL'
INSERT INTO trucks (name, max_volume_m3, waste_carrier, landfill_id, available)
SELECT 'Šiukšliavežė ' || lpad(i::text, 2, '0'), i,
       (ARRAY['Kauno švara','Biomotorai','Ecoservice','Ekonovus'])[((i-1)%4)+1],
       ((i-1)%3)+1, i % 2 = 1
FROM generate_series(1,21) i;
INSERT INTO sites(site_key,address,latitude,longitude)
VALUES ('address:synthetic truck site','Synthetic truck site',54.6872,25.2797)
RETURNING id AS site_id \gset
INSERT INTO bins(site_id,external_id,waste_type,latitude,longitude)
VALUES (:site_id,634,'Mixed municipal waste',54.6872,25.2797)
RETURNING id AS bin_id \gset
INSERT INTO bin_hist(bin_id,date,was_serviced,fill_level)
VALUES (:bin_id,'2026-10-08 06:00:00',true,3);
SQL
```

From `backend/`, run `uv run alembic upgrade head` twice and
`uv run alembic check`. Expect revision `0007` with no further upgrade or schema
drift. Inspect `\d trucks`, `\d landfills`, `\d sites`, `\d bins` and `\d bin_hist`: truck
constraints and collection references remain valid. All 21 trucks and the
synthetic collection chain remain unchanged on repeated upgrade. Fresh and
populated replacement verification is in the data-foundation procedure.

Revision `0005` requires an empty **legacy** truck table, including retired
rows. It never converts site counts to volume, invents a carrier or deletes
records. Its guard runs only when applying the revision, not on later startup.
The downgrade to `0004` also refuses any truck rows because volume cannot be
converted back to a site count and dropping carrier values would lose data.
Revision `0004` deliberately discarded old collection data and cannot downgrade
further. Historical `0003` guards belong in a separate database pinned to
`0002`/`0003`; do not change those historical revisions.

For the guarded transition, use a **second empty disposable database**, not the
21-truck fixture database. From `backend/`, export that database's URL and run:

```bash
uv run alembic upgrade 0004
```

Insert a synthetic legacy truck in psql connected to that second database:

```sql
INSERT INTO trucks(name,max_bins_per_trip,available,deleted)
VALUES ('Synthetic legacy truck',18,false,true);
SELECT * FROM trucks;
```

`uv run alembic upgrade 0005` must fail, identifying the truck ID and explaining
that site counts cannot identify volume and carrier is unknown. Inspect
`alembic_version` and `trucks`: revision `0004`, old columns and original row
must be intact. Repeat with a nondeleted available/unavailable fixture. Remove
only that owned disposable fixture, then upgrade to `0005` successfully. Keep this historical volume-guard check pinned to `0005`; it does not exercise landfill rollback. Retain an
existing Site/Bin/BinHist/import-checkpoint chain before this upgrade and compare
all values/references afterward: no changes are allowed.

With that second database's trucks still empty, `uv run alembic downgrade 0004`
then `uv run alembic upgrade 0005` must succeed. Insert a valid volume truck
with `waste_carrier='Kitas vežėjas'`: it must be accepted without a schema change.
Downgrade must now fail unchanged; repeat with a retired volume truck. Direct
SQL writes with volume `0`, `-1`, `'NaN'`, `'Infinity'`, `'-Infinity'` or NULL must
reject. Positive `0.5`, `120` and `0.0000000001` must persist unchanged. Inspect
`\d trucks`: seven fields (nullable landfill reference), NUMERIC without a fixed scale, TEXT carrier,
generated identity, name and retirement checks, finite positive volume check,
and **no carrier-name constraint**. Restore the main verification connection
before API/browser checks. Never run fixture cleanup against application storage.

## Landfill migration and storage verification (revision 0006)

The self-contained migration snapshot comes from the supplied
`vilnius_waste_facilities.geojson`, SHA256
`1e588cb980c105d287497f202fc4e342d9fee3940d2e37fda7a586d68185e42b`.
Treat its descriptions, status and verified_at as supplied provenance; no
external source checks or operational route guarantees are implied.

| Generated ID | Source ID | Latitude | Longitude |
|---|---|---|---|
| 1 | ecoservice-gariunu-71 | 54.6567 | 25.1563 |
| 2 | ekobaze-lentvario-13a | 54.652436 | 25.135007 |
| 3 | vaatc-mba-jocioniu-13 | 54.6669658 | 25.1583394 |

Inspect `SELECT * FROM landfills ORDER BY id` against all source features:
18 columns, generated INTEGER identity, original IDs in source_id, every
property, ordered waste_streams array, DATE verified_at, collection name and
description in dataset_name/dataset_description, and separate longitude and
latitude. No FeatureCollection/Feature/Point type fields are stored.
current_status_source is NULL for rows 1/2; municipal_arrangement_source is NULL
for row 3. No strings, URLs or descriptions are translated or fabricated.

Use a second disposable database to run `uv run alembic upgrade 0005`, insert
active and retired volume-based trucks plus a Site/Bin/BinHist/import-checkpoint
chain, and snapshot every column. Upgrade to `0006`; all original values must
remain identical, with landfill_id NULL for both trucks. Run the upgrade twice:
three catalog rows remain unchanged, without reseeding or source access.
Insert a disposable fourth landfill by copying row 1's fields with a distinct
source_id and omitting its ID: the generated ID must be 4. Remove only that
owned fourth fixture afterward.

In this disposable database, set the active truck's landfill_id to 1. An unknown
ID must fail the FK, and deleting landfill 1 must be rejected. Downgrade to
`0005` must fail identifying that assigned Truck, preserving schema/version and
all data. Repeat with only a retired Truck assigned: it must also fail. When
all references are NULL, downgrade to `0005` then upgrade to `0006` must succeed,
preserving existing trucks and collection/import snapshots and restoring the
three catalog seeds. Never clear operational assignments to make rollback work.
Fresh full-chain upgrade and `uv run alembic check` must also succeed.

## API verification

Return to the main disposable connection in `backend/` and start the normal entrypoint:

```bash
sh start.sh uv run uvicorn app.main:app --host 127.0.0.1 --port 58000
```

Schema preparation precedes serving. OpenAPI should document six truck endpoints, including the statistics route, plus read-only `GET /landfills`. Router/schemas are grouped under `app/interfaces/trucks/`; bin-sync CLI is under `app/interfaces/bin_sync/`. Its retained invocation is `uv run python -m app.interfaces.bin_sync`; verify against the controlled VASA procedure in `docs/data-foundation-verification.md`, with exit 0 for full success, 2 for a limited trial and 1 for an unreachable source. Only this explicit command performs VASA I/O. The configured unreachable VASA URLs must not prevent startup or truck CRUD.

```bash
curl -sS 'http://127.0.0.1:58000/landfills'
curl -sS 'http://127.0.0.1:58000/trucks?page=1'
curl -sS 'http://127.0.0.1:58000/trucks?page=2'
curl -sS 'http://127.0.0.1:58000/trucks?page=3'
curl -sS 'http://127.0.0.1:58000/trucks?page=4'
curl -sS 'http://127.0.0.1:58000/trucks/stats'
curl -sS 'http://127.0.0.1:58000/trucks?available=true&min_max_volume_m3=5&max_max_volume_m3=15'
curl -i 'http://127.0.0.1:58000/trucks?page=0'
curl -i 'http://127.0.0.1:58000/trucks?min_max_volume_m3=40&max_max_volume_m3=20'
```

Expect page items ordered by ID: 10, 10, 1 then 0, total 21 and page_size 10. Statistics return total 21, available_count 11 and average_max_volume_m3 11.0, independent of list filters/pages. On an empty fleet expect 0/0/null. Retired rows never contribute to any aggregate; `/trucks/stats` must resolve as a static route, while `/trucks/1` still returns eligible detail. The available/5–15 m³ filter gives 6 matches. Adding carrier `Ecoservice` gives 3 (volumes 7, 11, 15); `Ecoservice partner` must not match. Query carrier names with `curl --get --data-urlencode 'waste_carrier=Kauno švara'`. Bounds 0.5/120.25 are valid; zero, negative, nonnumeric, NaN or infinite bounds reject. Blank carrier/search have no effect. Invalid page/inverted bounds return `422`. Add manual name searches with Lithuanian case variants and literal `%`, `_` and backslash names; totals must count only matching nondeleted records and the same predicates as items.

Create a temporary truck, note its returned ID and use that ID in subsequent calls:

```bash
curl -i -X POST http://127.0.0.1:58000/trucks \
  -H 'Content-Type: application/json' \
  -d '{"name":"  Synthetic temporary truck  ","max_volume_m3":18.5,"waste_carrier":"Ecoservice","landfill_id":1,"available":true}'
curl -i -X POST http://127.0.0.1:58000/trucks \
  -H 'Content-Type: application/json' \
  -d '{"name":"Invalid","max_volume_m3":0,"waste_carrier":"Ecoservice","landfill_id":1,"available":true}'
```

Create returns `201` with exactly `id`, `name`, `max_volume_m3`, `waste_carrier`, `landfill_id`, `available`: trimmed name/carrier and numeric volume, without `deleted` or the removed capacity field. SQL shows deleted false. Try volumes 0, -1, numeric strings and booleans; missing/null fields; blank/nonstring names or carriers; nonboolean availability; and extra `id`/`deleted`/`max_bins_per_trip`/unknown fields. All must reject without mutation. Raw JSON NaN/Infinity/-Infinity and an overflowing `1e400` must return `422` with JSON field detail rather than failing to encode the invalid input. Volumes 0.5, 18.5 and 120, duplicate names and explicit available false must succeed. A nonempty unlisted carrier such as `Kitas vežėjas` is accepted at the API and returned faithfully.

For the temporary ID, PATCH only availability and verify name/volume/carrier/landfill remain unchanged; PATCH `{}` returns the unchanged representation. Supplied null/unknown fields reject. DELETE returns bodyless `204`; subsequent detail, edit and repeat delete return `404`. Also PATCH only volume and only carrier, preserving other fields. SQL must show retained deleted true/available false. Competing valid PATCH/DELETE requests may finish in either order but must never leave a retired truck available or editable.


`GET /landfills` returns a three-row array in generated-ID order, with the full
18-field mapping described above, numeric coordinates, ordered waste-stream
arrays and ISO date strings. Compare names/source IDs/URLs/metadata to the
embedded source snapshot; there are no write routes. POST requires landfill_id;
PATCH accepts it as a strict existing positive integer. Missing create selection,
null, numeric strings, booleans, fractions, zero/negative and unknown IDs return
`422` with loc ending in landfill_id, without mutation. Changing only landfill
preserves other fields; omitting it preserves an assigned Truck's choice.

For a transitional unassigned case, insert an owned synthetic Truck with
landfill_id NULL through SQL in this disposable database. Its list/detail
representation must include null. Empty PATCH returns it unchanged; a nonempty
PATCH omitting landfill returns field-addressable `422`. PATCH landfill_id 2
assigns it while preserving other fields. Retire the fixture; SQL must retain 2,
deleted true and available false. Creating an unlisted carrier still succeeds
when a valid landfill is supplied.

In disposable storage only, use a temporary failing insert/update trigger to simulate a database error; the endpoint must return a generic `500` and retain original values. Remove the trigger before continuing. Verify responses do not contain SQL, connection details or exception traces. Restart the backend and confirm committed values survive, shutdown completes normally and there were no VASA requests.

For repeatable PATCH/DELETE calls, replace `TRUCK_ID` with the temporary truck's generated ID:

```bash
TRUCK_ID=22
curl -i -X PATCH "http://127.0.0.1:58000/trucks/$TRUCK_ID" \
  -H 'Content-Type: application/json' -d '{"available":false}'
curl -i -X PATCH "http://127.0.0.1:58000/trucks/$TRUCK_ID" \
  -H 'Content-Type: application/json' -d '{}'
curl -i -X DELETE "http://127.0.0.1:58000/trucks/$TRUCK_ID"
curl -i "http://127.0.0.1:58000/trucks/$TRUCK_ID"
```

For controlled rollback verification, install this trigger in the disposable database, PATCH any eligible truck and inspect that its values are unchanged. Remove both objects immediately afterward:

```sql
CREATE FUNCTION truck_verification_failure() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Synthetic persistence failure'; END;
$$;
CREATE TRIGGER truck_verification_failure BEFORE UPDATE ON trucks
FOR EACH ROW EXECUTE FUNCTION truck_verification_failure();
-- Make the HTTP PATCH now; expect generic 500 and unchanged storage.
DROP TRIGGER truck_verification_failure ON trucks;
DROP FUNCTION truck_verification_failure();
```

## Nullable landfill details verification (revision 0007)

Before browser checks, verify nullable catalog details at head `0007` in a
disposable database. Upgrade an initialized `0006` database containing assigned
trucks and compare complete catalog/Truck/collection snapshots: all values must
remain unchanged. Run `uv run alembic check` and inspect catalog nullability:
only `id` and `name` must be NOT NULL. In that disposable storage only:

```sql
INSERT INTO landfills (name) VALUES ('Tik pavadinimas') RETURNING *;
SELECT column_name, is_nullable FROM information_schema.columns
WHERE table_name = 'landfills' ORDER BY ordinal_position;
```

The inserted facility has a generated ID and NULL in every other detail column.
`GET /landfills` must return its name/ID and explicit nulls, including coordinates,
source IDs, arrays and date. Use its returned ID in a valid Truck POST/PATCH:
assignment still succeeds. Required name, generated identity, nonnull source-ID
uniqueness and geographic range checks still apply; multiple NULL source IDs are
allowed. A fresh base-to-head upgrade still seeds original rows 1–3 and next ID 4.

With this incomplete row present, `uv run alembic downgrade 0006` must fail with
its ID and leave schema/data/version unchanged. Resolve missing details
deliberately, or remove only this owned unreferenced scratch row, then verify
downgrade restores revision 0006's NOT NULL detail columns; reupgrade to head
preserves all remaining values. The two source-URL columns already optional at
0006 stay nullable throughout. Do not run this fixture or rollback on
operational storage.

## Browser verification

Use the native backend above. From `frontend/`, run:

```bash
npm ci
npm run lint
npm run build
VIPTOP_API_PROXY_TARGET=http://127.0.0.1:58000 npm run dev -- --host 127.0.0.1 --port 55173
```

In another terminal, verify the built frontend as well:

```bash
VIPTOP_API_PROXY_TARGET=http://127.0.0.1:58000 npm run preview -- --host 127.0.0.1 --port 54173
```

Open `http://127.0.0.1:55173/`, choose `Administratorius`, and confirm `/admin/trucks`. `Vairuotojas` is visibly disabled; the admin navbar opens the truck screen. Check browser Back/Forward, direct opening and reload of `/admin/trucks`. Repeat direct opening/reload on `http://127.0.0.1:54173/admin/trucks`. Both servers proxy `/api/trucks` and `/api/landfills` to the native backend; no browser API-host setting or CORS configuration is needed.

With the initial 21-record fixture, perform these steps before retiring fixture rows:

1. Confirm 10 rows on pages 1 and 2 and one on page 3, correct indicators and disabled first/last navigation buttons. Navigate back and forth, retaining filters. Empty storage, a single match and exactly 10 matches each disable unnecessary navigation. The footer remains usable at 320 pixels.
2. On page 3, search for `ŠIUKŠLIAVEŽĖ 02`; expect page 1 and one match. Clear filters; select each availability choice and optional volume bounds and carrier dropdown, including the combined available/5–15 filter (six matches). Minimum greater than maximum shows a field error and sends no request. An unmatched search shows a no-match message distinct from an empty database.
3. Add a truck: name/volume start blank, no carrier or landfill is selected and `Prieinamas` starts enabled. The labels read `Maksimali talpa` with a clear `m³` unit, `Atliekų vežėjas` and `Sąvartynas`. The carrier select contains only Kauno švara, Biomotorai, Ecoservice and Ekonovus; no free-text field exists. The landfill select contains all three exact names returned by `/api/landfills`, with no default choice. Cancel, reopen, and verify fresh defaults and no persisted record. Reject blank names, missing carrier/landfill and blank/zero/negative/nonfinite volume without requests. Save 0.5, 18.5 and 120 m³ with each company and each facility, accepting comma or point decimal input and sending numeric volume and landfill ID. Also save an explicitly unavailable truck.
4. Open a row/name to edit; confirm all values and the assigned landfill name are preloaded. Cancel changes without persisting. Change the selected facility, save, reopen and reload to confirm persistence. Save an edit, retaining the current filter/page. An edit that no longer matches the filter disappears. Adding on a later page preserves that page when it remains valid.
5. Click the separate red delete action; it opens only confirmation, naming the selected truck. Cancel makes no request. Confirm deletion; it disappears after refresh. Delete the only match on the last page and confirm recovery to the preceding valid page; deleting the final match recovers to page 1 with the appropriate empty/no-match message.
6. Use only Tab, Shift+Tab, Enter/Space and Escape for filters, pagination, create, edit and delete. Confirmation initially focuses `Atšaukti`. Closing restores focus to the initiating control; after that row disappears, focus goes to `Pridėti šiukšliavežę`. Check dialogs and actions at desktop and 320-pixel widths without horizontal scrolling or obscured controls.

Also verify the refined layout and direct navigation:

- Leaf branding appears on role selection/admin; the background is neutral gray. At a 1440-pixel desktop viewport, the approximately 1280-pixel container aligns the navbar, heading, overview, filters, actions and table. At 320 pixels there is no horizontal overflow and controls wrap in reading order.
- `Pridėti šiukšliavežę` then `Išvalyti filtrus` are always visible above the table, aligned right, with equal width/height, matching text/padding and a filled clear background. Check both side-by-side desktop and stacked 320-pixel layouts. Clear resets filters/page even from an unfiltered later page. The table/mobile volume label reads `Maksimali talpa`, and the carrier column reads `Atliekų vežėjas`; 18 and 18.5 display `18 m³` and `18,5 m³`. The availability circle must remain inside its card when it wraps at 320 pixels, without overlapping following filters.
- Submit page 3 through the labeled `Puslapis` input, once with Enter and once with `Eiti`; expect one row and preserved filters. Previous/next, clear and last-page deletion synchronize input and indicator. Blank, 0, 1.5, nonnumeric and beyond-last input produce a Lithuanian error without a request. All page navigation is disabled during loading/failure/no matches.
- The fleet overview appears before filters: initial values 21, 11,0 m³ and 52% (11 of 21). Filter to one row and navigate pages; these values remain unchanged. Empty data shows 0/—/0% and `0 iš 0`. The available/total count beneath its title has the same font size/weight as the total/average values; the circle stays readable and wraps if necessary at 320 pixels. Verify 0%/50%/100% fixtures, accessible text and an arc matching the unrounded ratio. Check average rounding using fractional means.
- Create, change volume/carrier/availability and retire a synthetic truck. Both overview and list refresh; list-only retry leaves statistics alone and statistics-only retry leaves the list alone. Delaying an obsolete statistics response after a mutation must not replace newer values. Failed statistics show an error rather than fake zeros.
- At 320/639 pixels, navbar links are initially hidden behind a labeled hamburger toggle; closed links are excluded from Tab navigation. Use Enter/Space to open, select the truck link to close, and Escape to close with focus returned to the toggle. At 640 pixels and desktop, links are visible directly and the toggle is hidden. Open on mobile, resize to desktop and back, and verify the mobile menu closes; reload/direct navigation also starts closed.
- Successful create/edit closes the modal and shows a top-right success toast, with no inline save-success paragraph. Check `Šiukšliavežė išsaugota.`, an accessible success announcement, close control and automatic dismissal after approximately five seconds (paused while hovered/focused). Failed save requests show an error toast above the open editor with its values preserved. Verify the close control or Escape dismisses the toast without closing the editor and the error announcement is accessible. Field errors remain beside inputs. Check top/right positioning and viewport fit at 320 pixels, and emulate reduced motion to confirm entry animation is disabled without hiding the feedback.

Create a temporary `Kitas vežėjas` truck through POST and inspect it in the
list: its original carrier and numeric volume must display faithfully. The
editor must show `Dabartinis atliekų vežėjas: Kitas vežėjas`, leave the carrier
select unselected, and prevent save until a listed carrier is explicitly
chosen. Opening/cancelling does not change that stored name. Retire only this
synthetic fixture afterward. In the filter, verify the same four companies plus
`Visi vežėjai`, exact carrier matching with name/availability/volume predicates,
page-1 resets and complete clear/reset behavior. Use decimal `5,0`/`15` bounds;
with the initial fleet, available Ecoservice trucks give 3 matches.

In the editor and both volume filters, type arbitrary letters and paste mixed
text such as `18 m3`: the previous value must remain unchanged. Clear each
control, type `18,5`, and paste `18.5`; both must be accepted and normalized to
numeric 18.5 for saving/filtering. Clearing and unfinished numeric input remain
possible; zero and nonfinite values still fail validation before submission.

In this disposable database, insert a synthetic truck with `landfill_id=NULL`
through SQL to represent a pre-0006 truck. Opening its editor must show
`Pasirinkite sąvartyną`, while preserving name, volume, carrier and availability.
Cancel and confirm SQL still shows NULL. A nonempty save without selection must
make no mutation. Select a named facility, save, reopen and confirm its numeric
ID and name persist. Retiring the truck must retain the reference while setting
deleted true and available false. Do not automatically choose a facility from
its operator or waste carrier. At 320 pixels, check every long facility name in
both the options and selected value, including keyboard selection with arrows,
Home/End and Enter, without clipping or horizontal overflow.

Truck UI and its API/types helpers are grouped under `frontend/src/pages/trucks/`. Shared pagination is under `frontend/src/components/table-pagination.tsx` and takes page/pageSize/total/state/callback without truck request logic.

Use browser developer tools to inspect and temporarily interrupt requests on this disposable environment. Restore connectivity after each scenario:

- Delay `/api/landfills` while opening the modal: `Kraunami sąvartynai…` appears and selection/save are disabled. Cancel remains usable. Release the obsolete response after closing and reopen; previous form values must not reappear.
- Fail `/api/landfills`: show `Nepavyko įkelti sąvartynų.` and `Bandyti dar kartą`, with save disabled. Enter name/volume/carrier, restore the lookup and retry; entered values remain, all names load, and an explicit selection permits save. A controlled empty-array response shows `Šiuo metu nėra sąvartynų.` and prevents saving. Cancellation must remain available in all three states.
- Submit a controlled unknown landfill ID to the real backend: its `422` maps to `Pasirinkite sąvartyną.` near the selector, with form values preserved and no mutation. Restore the valid numeric selection and retry successfully.
- Throttle the list request, change page/filter while an earlier request is delayed, and confirm only the latest items, total and page appear. Navigation is disabled while loading; there is no flash of stale results.
- Block `/api/trucks*` and change a filter: expect the list error and disabled pagination. Unblock and choose `Bandyti dar kartą`; the current query succeeds.
- Block mutation requests before saving/deleting. Expect preserved form values or confirmation context and a concise Lithuanian error. Unblock and retry successfully. While a request is pending, repeated clicks/Enter must not issue duplicate mutations.
- Let POST/PATCH/DELETE succeed, then block only its subsequent list GET or `/api/trucks/stats` GET. The dialog closes; a save's success toast (or deletion's existing notice) is shown alongside the appropriate list/statistics refresh error. A successful save does not become an error toast because a read failed, and its toast may dismiss normally while the read error remains actionable. Retrying the failed read must not repeat the mutation, emit another save toast or refetch the other successful read. Developer tools' request breakpoints or a temporary local request interceptor can distinguish methods; no application changes are necessary.
- Retire a truck from a second client while its editor is open. Saving returns the missing/deleted message; refresh or dismiss it to recover, without reviving the truck.

## Historical preservation

Before retiring referenced truck 1 in the UI, capture the fixture records from the repository root:

```bash
docker exec viptop-truck-ui-db psql -X -A -t -U viptop -d viptop_truck_verify \
  -c 'SELECT row_to_json(s) FROM sites s ORDER BY id; SELECT row_to_json(b) FROM bins b ORDER BY id; SELECT row_to_json(h) FROM bin_hist h ORDER BY id' \
  > /tmp/viptop-truck-history-before.txt
```

Delete `Šiukšliavežė 01` through confirmation. Run the same command with output `/tmp/viptop-truck-history-after.txt`, then `diff -u /tmp/viptop-truck-history-before.txt /tmp/viptop-truck-history-after.txt`: expect no differences. Inspect the retained truck and independent collection history:

```sql
SELECT id, name, max_volume_m3, waste_carrier, landfill_id, available, deleted FROM trucks WHERE id=1;
SELECT h.id,h.bin_id,h.date,h.was_serviced,h.fill_level
FROM bin_hist h JOIN bins b ON b.id=h.bin_id
ORDER BY h.date,h.id;
```

Truck 1 keeps its ID/name/volume/carrier/landfill and now has available false/deleted true. Every reference/value in the captured collection records remains unchanged; collection history requires no truck join. GET `/trucks` excludes it, GET `/trucks/1` and PATCH `/trucks/1` return `404`. History is independent of the truck management detail endpoint.

## Packaged startup, persistence and cleanup

On a separate disposable Compose project, use a temporary env file with the example connection settings and the unreachable VASA URLs above. Keep operational `.env` and storage untouched. If standard ports are occupied, use an override file changing all three published ports. To verify packaged files, reset the frontend/backend bind mounts to `[]` in that override; environment settings supply the database connection. Compose automatically sets `VIPTOP_API_PROXY_TARGET=http://backend:8000`.

```bash
docker compose --env-file /tmp/viptop-truck-ui.env -p viptop-truck-ui-verify config --quiet
docker compose --env-file /tmp/viptop-truck-ui.env -p viptop-truck-ui-verify up --build -d
docker compose --env-file /tmp/viptop-truck-ui.env -p viptop-truck-ui-verify logs backend
docker compose --env-file /tmp/viptop-truck-ui.env -p viptop-truck-ui-verify exec backend \
  ls alembic/versions/0007_nullable_landfill_details.py
```

Add `-f docker-compose.yml -f /tmp/viptop-truck-ui-compose.yml` before the action in every command when using an override. Logs must show migration through `0007` before application startup. Load the container frontend, create/edit trucks, and repeat two-page navigation/filters/deletion against a 21-truck synthetic fleet. SQL `generate_series` as above can prepare it, omitting history inserts and using the Compose database's name. IDs continue after any earlier fixture operations; find rows by their synthetic names.

Record a committed edited row and the retired row's flags. Restart only the backend with `docker compose ... restart backend`, reload the browser, and compare API/SQL values. They must persist; startup/shutdown is normal with no VASA requests. Run `docker compose ... exec backend uv run alembic check` for schema agreement.

After recording results, stop native backend/frontend/preview processes, run `docker compose ... down --volumes` for the owned disposable project, and remove `viptop-truck-ui-db`. Remove owned temporary env/override/snapshot files. Do not remove unrelated containers, databases, volumes or images.

## Recorded nullable-landfill results — 2026-10-10

Revision `0007` was checked in two owned disposable PostgreSQL 17 databases in
Podman on port 55435, with native backend startup and HTTP calls on 58002.
Fresh base-to-head and populated-0006 upgrades passed; complete catalog, Truck,
collection and import snapshots were unchanged on the populated upgrade.
Only `id` and `name` remained NOT NULL. Name-only facilities stored NULL in all
16 details; multiple NULL source IDs were accepted, while nonnull source-ID
uniqueness, required name/generated identity and coordinate ranges remained
enforced. Original seed IDs stayed 1–3 with next generated ID 4.

Incomplete downgrade failed with the affected facility IDs and unchanged
schema/data/version. After removing only owned unreferenced scratch rows,
complete downgrade and reupgrade preserved all remaining values. Alembic
schema comparison passed for both databases. Real lookup HTTP and OpenAPI
accepted null strings, coordinates, arrays and date; Truck create/reassignment/
retirement succeeded using a name-only facility, preserving its reference.
Frontend build/lint, focused Ruff and strict OpenSpec validation passed; the
existing large-chunk build warning remained. This follow-up changed no UI
controls; browser/packaged Compose verification was not repeated.

## Recorded landfill-extension results — 2026-10-10

Verification used PostgreSQL 17 in the owned disposable Podman container
`viptop-landfill-verify` on port 55434, native backend startup on 58001, Vite
development on 55174 and rebuilt preview on 54174. The seeded 21-truck fixture
started with 11 available trucks and mean volume 11.0 m³. The in-app browser
was unavailable; standalone Chromium verified the real UI/backend proxy, with
mobile screenshots inspected. Operational application storage was not used.

- Revision 0006 passed fresh-chain and populated-0005 upgrades, repeated head upgrades and Alembic schema comparison. All 18 catalog columns matched the supplied GeoJSON, including exact source IDs, dataset metadata, arrays, dates, URLs, absent-property NULLs and separate coordinates. Generated IDs were 1–3 and the next generated ID was 4. Source SHA256 matched the documented snapshot.
- Existing active/retired trucks remained unassigned on upgrade; collection and import snapshots remained identical. Invalid FK assignments and deleting a referenced facility were rejected. Downgrade refused active and retired references without schema/data/version changes; deliberately unassigned rollback and reupgrade preserved existing trucks.
- Actual HTTP checks passed the full ordered catalog and six-field truck responses. Required create, strict integer/existing-ID validation, assigned partial edits, unassigned edit requirements, empty PATCH and field-addressable 422 feedback behaved as documented. Retirement retained its reference and excluded the row from management reads. Concurrent edits/deletion and a controlled database failure preserved transaction semantics. No landfill management write routes were exposed.
- Development-browser checks passed all three named choices, numeric ID payloads, real create/edit/reopen/cancel/retire, no default assignment and editing a legacy unassigned truck. Loading, failed and empty catalog responses prevented saves while cancellation remained usable. Retry preserved inputs; closing discarded obsolete responses. A controlled unknown-ID request reached the real API, showed the inline field error without mutation, then succeeded with a valid selection.
- At 320 pixels, full long names wrapped in options and selected values without horizontal overflow. Keyboard selection, modal/confirmation focus, numeric-only decimal input and repeated-submit protection passed. The browser reported no JavaScript errors. Existing volume/carrier filters and statistics retained their API behavior, including the initial 10/10/1 pages and the six/three combined-filter matches.
- The built preview passed direct-link reloads and real create/edit through `/api/trucks` and `/api/landfills`. A saved edit to volume 25.5 and landfill 2 survived backend restart and browser reload with the correct selected name. Complete before/after snapshots of landfills, active/retired trucks, collection and import tables were identical. Native startup reapplied head safely without source-file access or VASA activity.
- Frontend lint/build, focused Ruff checks, Alembic schema agreement and strict OpenSpec validation passed. Build retained the existing large-chunk warning. Packaged Compose was not rerun for this extension; native startup and both frontend proxies supplied the runtime evidence here. Earlier packaged results below describe their respective historical revisions.

## Recorded volume/carrier results — 2026-10-10

Verification used native FastAPI through `backend/start.sh`, Vite development
and a freshly built Vite preview, backed by isolated PostgreSQL 17 in the owned
rootless Podman container `viptop-truck-update-verify`. The fleet was synthetic:
21 trucks with volumes 1–21 m³, alternating availability and the four UI
carriers. Application storage and operator settings were not used.

- Fresh migration to `0005`, upgrade from initialized `0004` with collection/import fixtures, repeated upgrade after creating trucks, and empty-table downgrade/re-upgrade passed. Active and retired trucks blocked incompatible upgrade/downgrade with diagnostic IDs and unchanged records, schema and migration version. Site/Bin/BinHist/import/checkpoint snapshots survived the transition unchanged; `alembic check` reported no model drift.
- Storage accepted fractional/tiny/above-99 volumes and an unlisted carrier as ordinary TEXT. Zero, negative, NaN and infinite volumes were rejected. Truck metadata retained exactly six required columns, identity/name/retirement invariants and no carrier-name constraint; historical migrations were unchanged.
- Actual HTTP requests covered all six endpoints, numeric five-field representations, strict mutation types/null/extra-field errors, omitted PATCH fields and `{}`, trimmed future carrier names, exact AND/inclusive filters, literal name searches, pagination and independent statistics. Raw nonfinite JSON and invalid bounds returned JSON `422` errors. A temporary failing-update trigger rolled back with a generic `500`; competing PATCH/DELETE requests preserved retirement. Retired detail/edit/re-delete returned `404`, and collection snapshots remained unchanged.
- Development-browser checks passed real create/edit round trips for every carrier, comma/point fractional inputs, values above 99, fresh defaults, validation without mutation, cancel/reset, combined filters, page resets and recovery after deleting the only last-page row. Empty-fleet statistics rendered 0/—/0%; displayed averages matched the backend and stayed independent of filters. An unlisted carrier remained visible and unchanged on open/cancel; saving required an explicit current-option choice.
- Standalone Chromium checks and visual screenshot inspection covered desktop and 320-pixel rows/modals, green-check/red-cross indicators, visible units, labeled controls and keyboard/focus restoration. Built-preview checks also covered 639/640-pixel navigation, long unbroken truck/carrier names, direct navigation/reload, reduced motion, toast positioning, hover-paused dismissal and error-toast dismissal with form values preserved. Wrapping fixes keep long truck names inside the row and the mobile availability circle inside its card.
- Interrupted saves preserved inputs and retried successfully; repeated pending submission issued one mutation. A committed save retained its success feedback when the following list or statistics request failed. Retrying issued only the failed GET, without another mutation or refetch of the successful read. Obsolete delayed filter and statistics responses could not replace newer results. Backend restart preserved the edited volume/carrier/availability, retired flags, complete row snapshots, pages/statistics and collection/import records; built-preview reload displayed the persisted edit.
- `npm run build`, `npm run lint`, focused backend Ruff checks, `alembic check` and strict OpenSpec validation passed. The build retains its existing large-chunk warning. Startup/restart worked with unreachable VASA endpoints; no import or optimizer was invoked. No automated test files or dependencies were added.

The in-app browser was unavailable, so browser verification used standalone
Chromium. Docker access was unavailable during discovery; Podman supplied the
disposable database for apply verification. Packaged Compose execution was not
repeated for this change; the native migration entrypoint and both real Vite
proxies were exercised. Owned verification servers, database container and
temporary fixtures were removed after recording results.

The numeric-input follow-up was verified in standalone Chromium against the
running frontend with intercepted Truck API responses: all three controls
rejected typed/pasted nonnumeric text, preserved prior values, supported
clearing and comma/point decimals, and emitted numeric create/edit values and
normalized filter bounds. Positive/finite validation and 320-pixel layout
checks passed, as did frontend build/lint and strict OpenSpec validation. No
backend behavior changed in this follow-up.

## Historical recorded initial-slice results — 2026-10-08 (twenty-row baseline)

Verification used disposable PostgreSQL 17 databases and a separate Compose project through rootless Podman, because the local Docker daemon was inaccessible. The packaged frontend/backend had no source bind mounts. All fixture records were synthetic.

- Empty/populated upgrade, repeated upgrade, Alembic schema comparison, incompatible-data rollback and guarded downgrade passed. Database constraints also rejected Unicode whitespace-only names consistently with API trimming.
- API pagination (20/1), filtered totals, Lithuanian/literal substring matching, strict mutation validation, partial/empty updates, missing/deleted exclusions, concurrent retirement and controlled persistence rollback passed.
- Native development, built preview and packaged Compose proxies/deep links worked. Desktop and 320-pixel browser checks covered navigation, filters, pagination, CRUD, form resets, keyboard operation, confirmation focus and focus restoration.
- Delayed responses, interrupted CRUD/list requests, retries and committed mutation followed by failed list refresh preserved the intended state. Last-page deletion recovered correctly; CRUD caused no full-page navigation.
- UI retirement of the referenced truck preserved complete Bin/Route/RouteStop/ServiceEvent snapshots. Historical joins retained truck attribution; list/detail/edit excluded the truck and its flags became deleted true/available false.
- Frontend lint/build, focused backend Ruff checks, Compose configuration validation and packaged Alembic schema comparison passed. Committed edits survived backend restart and browser reload; packaged startup applied `0003` before serving with no GIS import.
- Native shutdown completed normally. Owned verification containers, volumes, images, server processes and temporary fixtures/settings were removed after verification; operational storage was not used.

## Historical recorded refinement results — 2026-10-08 (ten-row version)

The refined version was verified against fresh disposable PostgreSQL 17 storage and rebuilt frontend/backend images without source bind mounts, using a separate rootless Podman Compose project. All fixtures were synthetic; the earlier twenty-row results above describe the initial implementation only.

- API pages for 21 trucks returned 10/10/1 items, with matching totals, fixed page_size 10, ascending IDs and no overlap; invalid pages and empty out-of-range pages retained the specified status/envelope behavior.
- Whole-fleet statistics passed empty, mixed availability, arithmetic mean, retirement exclusion and filter/page-independence checks. A controlled database failure returned a sanitized 500 and the original schema was restored.
- The retained bin-sync module command imported one controlled synthetic site with exit 0 and returned exit 1 for an unreachable source. Packaged module paths/migration 0003 were present; startup applied migration before serving, while startup/truck CRUD/statistics performed no GIS import.
- Desktop and 320-pixel screens passed leaf/gray-theme, aligned wider layout, always-visible right-aligned add/clear order, filled clear background, revised capacity label and overflow checks. Screenshots were inspected visually.
- Real 0/1/10/11/21 matching-fleet cases, previous/next, direct Enter/Eiti jumps, invalid input without requests, filter resets, input synchronization and last-page recovery passed. The reusable input also discarded stale draft/errors when returning to earlier pages.
- Empty and 0%/50%/100% overview fixtures passed, including the actual half-circle arc, Lithuanian one-decimal averages and accessible percentage labels. Filters/pages left whole-fleet values unchanged.
- CRUD refreshed both overview and list. Mutation failure preserved input; pending duplicate submissions were guarded. Failed list or statistics refresh after a committed save preserved its success notice, and retries repeated only the failed read. Delayed obsolete statistics did not replace newer values.
- Keyboard-only filtering/select/bounds, create cancellation/reset, creation, editing, confirmation and deletion passed at 320 pixels; confirmation focused cancel and removed-row focus returned to the relocated add action.
- Native development, built preview and packaged Compose proxies/deep-link reloads passed. Packaged list/detail/statistics were unchanged across backend restart; browser reload preserved edits and CRUD retained the same document.
- Frontend lint/build, focused backend Ruff checks, Compose configuration and Alembic schema comparison passed. No automated test files were added to the project.
- Native shutdown completed normally. Owned disposable containers, volumes, images, server processes and temporary verification files were removed; operational settings/storage and unrelated containers were left untouched.

## Historical recorded presentation results — 2026-10-08 (save toasts and mobile navigation)

Verification used native FastAPI against a separate disposable PostgreSQL 17 container and both Vite development and the rebuilt preview. The initial synthetic fleet had 27 trucks with capacities 1–27 and 24 available, producing `24 iš 27` and 89%. No operational data/settings were used. The in-app browser was unavailable; standalone Chromium checks and visual screenshot inspection covered the running system.

- Add/clear had equal measured width/height and matching font/padding, with the filled clear background retained, at 320/639/640/1440 pixels. Total, average and available/total counts shared their font size/weight; wrapping avoided horizontal overflow. The true empty fleet rendered 0/—/0%, `0 iš 0`, the neutral circle and usable equal actions.
- Mobile menu checks passed initially hidden links, keyboard opening/selection, closed-link exclusion from Tab order, Escape focus restoration, active navigation, 639/640-pixel transitions and deep-link reload. Desktop links remained directly visible.
- Real create/edit saves produced top-right success toasts without inline save-success text, preserved page/filter context and refreshed the list/overview. Client validation sent no mutation; a real backend 422 response retained field errors and produced a sanitized error toast. Interrupted saves preserved input/focus, kept the editor open and succeeded on retry. Repeated Enter during a delayed save issued one mutation.
- Error toasts remained visible and accessible above the editor. Close/Escape dismissed feedback without closing the editor; accessible error announcements were not hidden by the modal. Reduced-motion checks disabled entry animation. Automatic dismissal passed after previous manual dismissals; focus restoration also resumed the shared timer rather than leaving later toasts permanently paused.
- A committed save followed by controlled list or statistics read failure kept successful feedback and the separate read error. Each retry issued only its failed GET, with no repeated mutation, duplicate toast or unrelated overview/list fetch. The complete browser run reported no JavaScript errors or mutation-driven document reloads.
- Rebuilt preview passed direct navigation/reload, mobile menu, real create with a reduced-motion toast, retirement and return to the true empty overview/list, page 1 and logical add-button focus. Desktop and mobile screenshots were inspected.
- Frontend lint/build, strict OpenSpec validation and whitespace checks passed. No automated test files were added. Previously recorded storage/backend checks remain applicable; this presentation refinement required no backend or migration changes.
- Native backend shutdown completed normally; owned frontend/preview processes, disposable database container/storage and temporary verification scripts/screenshots were removed after recording results.
