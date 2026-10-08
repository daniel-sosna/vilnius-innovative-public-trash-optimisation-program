# Manual truck-management verification

Use disposable PostgreSQL storage and explicitly synthetic records. Do not run fixture inserts, downgrades, triggers or cleanup against operational storage. No automated test files are required.

## Disposable database and migration

The examples use a standalone database on port 55432. Use `podman` in place of `docker` if that is the available local engine. Create only resources you own:

```bash
docker run -d --name viptop-truck-ui-db -p 127.0.0.1:55432:5432 \
  -e POSTGRES_USER=viptop -e POSTGRES_PASSWORD=viptop \
  -e POSTGRES_DB=viptop_truck_verify postgres:17-alpine
```

From `backend/`, use these disposable settings. The unreachable GIS URL makes accidental source access visible; migrations and truck requests must not contact it.

```bash
export DATABASE_URL=postgresql+psycopg://viptop:viptop@127.0.0.1:55432/viptop_truck_verify
export BIN_SYNC_SOURCE_URL=http://127.0.0.1:1/query
export BIN_SYNC_HTTP_TIMEOUT_SECONDS=1
uv sync --locked
uv run alembic upgrade 0002
```

At the repository root, create a fleet spanning two pages and one historical reference chain:

```bash
docker exec -i viptop-truck-ui-db psql -v ON_ERROR_STOP=1 -U viptop -d viptop_truck_verify <<'SQL'
INSERT INTO trucks (name, max_bins_per_trip, available)
SELECT 'Šiukšliavežė ' || lpad(i::text, 2, '0'), i, i % 2 = 1
FROM generate_series(1,21) i;
INSERT INTO bins (id,lat,lon,address)
VALUES (634,54.6872,25.2797,'Synthetic truck verification site');
INSERT INTO routes (service_date,truck_id) VALUES ('2026-10-08',1);
INSERT INTO route_stops (route_id,bin_id,stop_order) VALUES (1,634,1);
INSERT INTO service_events (bin_id,service_ts,fill_level,duration,route_id)
VALUES (634,'2026-10-08T06:00:00Z','FULL',90,1);
SQL
```

From `backend/`, run `uv run alembic upgrade head` twice and `uv run alembic check`. Expect revision `0003`, then no further upgrade or schema drift. Inspect `\d trucks` and `\d routes` using psql: identities/restrictive references remain, deleted defaults to false, capacity is 1–99, names cannot be blank and deleted trucks cannot be available. All 21 original trucks remain nondeleted, with original values; the route/stop/event chain is unchanged. Repeat on an empty disposable database to verify fresh preparation.

For incompatibility verification, create a separate database, point `DATABASE_URL` to it, upgrade only to `0002` and insert capacity 100 and a whitespace-only name. `upgrade head` must exit nonzero identifying both truck IDs and reasons. Inspect `alembic_version` (still `0002`), the four original truck columns, and unchanged values. Correction is an operator decision, not part of migration.

For rollback, use initialized valid disposable storage with no retired trucks: downgrade to `0002` and upgrade again, checking values/references. On a separate disposable database at `0003`, insert a truck with deleted true and available false; downgrade must fail, retain revision `0003`, and retain the row/flags. Do not revive trucks just to permit rollback.

## API verification

Return to the main disposable connection in `backend/` and start the normal entrypoint:

```bash
sh start.sh uv run uvicorn app.main:app --host 127.0.0.1 --port 58000
```

Schema preparation precedes serving. OpenAPI should document six truck endpoints, including the statistics route. Router/schemas are grouped under `app/interfaces/trucks/`; bin-sync CLI is under `app/interfaces/bin_sync/`. Its retained invocation is `uv run python -m app.interfaces.bin_sync`; verify against the controlled synthetic GIS procedure in `docs/data-foundation-verification.md`, with exit 0 for successful import and exit 1 for an unreachable source. Only this explicit command performs GIS I/O. The configured unreachable GIS URL must not prevent startup or truck CRUD.

```bash
curl -sS 'http://127.0.0.1:58000/trucks?page=1'
curl -sS 'http://127.0.0.1:58000/trucks?page=2'
curl -sS 'http://127.0.0.1:58000/trucks?page=3'
curl -sS 'http://127.0.0.1:58000/trucks?page=4'
curl -sS 'http://127.0.0.1:58000/trucks/stats'
curl -sS 'http://127.0.0.1:58000/trucks?available=true&min_max_bins_per_trip=5&max_max_bins_per_trip=15'
curl -i 'http://127.0.0.1:58000/trucks?page=0'
curl -i 'http://127.0.0.1:58000/trucks?min_max_bins_per_trip=40&max_max_bins_per_trip=20'
```

Expect page items ordered by ID: 10, 10, 1 then 0, total 21 and page_size 10. Statistics return total 21, available_count 11 and average_max_bins_per_trip 11.0, independent of list filters/pages. On an empty fleet expect 0/0/null. Retired rows never contribute to any aggregate; `/trucks/stats` must resolve as a static route, while `/trucks/1` still returns eligible detail. The combined filter gives 6 odd-capacity matches from 5 to 15. Invalid page/inverted bounds return `422`. Add manual name searches with Lithuanian case variants and literal `%`, `_` and backslash names; totals must count only matching nondeleted records and the same predicates as items.

Create a temporary truck, note its returned ID and use that ID in subsequent calls:

```bash
curl -i -X POST http://127.0.0.1:58000/trucks \
  -H 'Content-Type: application/json' \
  -d '{"name":"  Synthetic temporary truck  ","max_bins_per_trip":35,"available":true}'
curl -i -X POST http://127.0.0.1:58000/trucks \
  -H 'Content-Type: application/json' \
  -d '{"name":"Invalid","max_bins_per_trip":100,"available":true}'
```

Create returns `201`, generated ID, trimmed name, deleted false; invalid capacity returns `422` with no row. Try capacities 0, -1, 1.5, strings and booleans; missing fields; null fields; blank names; nonboolean availability; and extra `id`/`deleted`/unknown fields. All must reject without mutation. Capacities 1 and 99, duplicate names and explicit available false must succeed.

For the temporary ID, PATCH only availability and verify name/capacity remain unchanged; PATCH `{}` returns the unchanged representation. Supplied null/unknown fields reject. DELETE returns bodyless `204`; subsequent detail, edit and repeat delete return `404`. SQL must show retained deleted true/available false. Competing valid PATCH/DELETE requests may finish in either order but must never leave a retired truck available or editable.

In disposable storage only, use a temporary failing insert/update trigger to simulate a database error; the endpoint must return a generic `500` and retain original values. Remove the trigger before continuing. Verify responses do not contain SQL, connection details or exception traces. Restart the backend and confirm committed values survive, shutdown completes normally and there were no GIS requests.

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

Open `http://127.0.0.1:55173/`, choose `Administratorius`, and confirm `/admin/trucks`. `Vairuotojas` is visibly disabled; the admin navbar opens the truck screen. Check browser Back/Forward, direct opening and reload of `/admin/trucks`. Repeat direct opening/reload on `http://127.0.0.1:54173/admin/trucks`. Both servers proxy `/api/trucks` to the native backend; no browser API-host setting or CORS configuration is needed.

With the initial 21-record fixture, perform these steps before retiring fixture rows:

1. Confirm 10 rows on pages 1 and 2 and one on page 3, correct indicators and disabled first/last navigation buttons. Navigate back and forth, retaining filters. Empty storage, a single match and exactly 10 matches each disable unnecessary navigation. The footer remains usable at 320 pixels.
2. On page 3, search for `ŠIUKŠLIAVEŽĖ 02`; expect page 1 and one match. Clear filters; select each availability choice and optional capacity bounds, including the combined available/5–15 filter (six matches). Minimum greater than maximum shows a field error and sends no request. An unmatched search shows a no-match message distinct from an empty database.
3. Add a truck: name/capacity start blank and `Prieinamas` starts enabled. The label reads `Maksimalus aikštelių skaičius per reisą`; the helper explains that a site can contain several containers. Cancel, reopen, and verify fresh defaults and no persisted record. Reject blank names, fractions and capacities 0/100; save valid capacities 1/99 and an explicitly unavailable truck.
4. Open a row/name to edit; confirm all values are preloaded. Cancel changes without persisting. Save an edit, retaining the current filter/page. An edit that no longer matches the filter disappears. Adding on a later page preserves that page when it remains valid.
5. Click the separate red delete action; it opens only confirmation, naming the selected truck. Cancel makes no request. Confirm deletion; it disappears after refresh. Delete the only match on the last page and confirm recovery to the preceding valid page; deleting the final match recovers to page 1 with the appropriate empty/no-match message.
6. Use only Tab, Shift+Tab, Enter/Space and Escape for filters, pagination, create, edit and delete. Confirmation initially focuses `Atšaukti`. Closing restores focus to the initiating control; after that row disappears, focus goes to `Pridėti šiukšliavežę`. Check dialogs and actions at desktop and 320-pixel widths without horizontal scrolling or obscured controls.

Also verify the refined layout and direct navigation:

- Leaf branding appears on role selection/admin; the background is neutral gray. At a 1440-pixel desktop viewport, the approximately 1280-pixel container aligns the navbar, heading, overview, filters, actions and table. At 320 pixels there is no horizontal overflow and controls wrap in reading order.
- `Pridėti šiukšliavežę` then `Išvalyti filtrus` are always visible above the table, aligned right, with equal width/height, matching text/padding and a filled clear background. Check both side-by-side desktop and stacked 320-pixel layouts. Clear resets filters/page even from an unfiltered later page. The table/mobile label reads `Max Aikštelių per reisą`.
- Submit page 3 through the labeled `Puslapis` input, once with Enter and once with `Eiti`; expect one row and preserved filters. Previous/next, clear and last-page deletion synchronize input and indicator. Blank, 0, 1.5, nonnumeric and beyond-last input produce a Lithuanian error without a request. All page navigation is disabled during loading/failure/no matches.
- The fleet overview appears before filters: initial values 21, 11,0 and 52% (11 of 21). Filter to one row and navigate pages; these values remain unchanged. Empty data shows 0/—/0% and `0 iš 0`. The available/total count beneath its title has the same font size/weight as the total/average values; the circle stays readable and wraps if necessary at 320 pixels. Verify 0%/50%/100% fixtures, accessible text and an arc matching the unrounded ratio. Check average rounding using fractional means.
- Create, change capacity/availability and retire a synthetic truck. Both overview and list refresh; list-only retry leaves statistics alone and statistics-only retry leaves the list alone. Delaying an obsolete statistics response after a mutation must not replace newer values. Failed statistics show an error rather than fake zeros.
- At 320/639 pixels, navbar links are initially hidden behind a labeled hamburger toggle; closed links are excluded from Tab navigation. Use Enter/Space to open, select the truck link to close, and Escape to close with focus returned to the toggle. At 640 pixels and desktop, links are visible directly and the toggle is hidden. Open on mobile, resize to desktop and back, and verify the mobile menu closes; reload/direct navigation also starts closed.
- Successful create/edit closes the modal and shows a top-right success toast, with no inline save-success paragraph. Check `Šiukšliavežė išsaugota.`, an accessible success announcement, close control and automatic dismissal after approximately five seconds (paused while hovered/focused). Failed save requests show an error toast above the open editor with its values preserved. Verify the close control or Escape dismisses the toast without closing the editor and the error announcement is accessible. Field errors remain beside inputs. Check top/right positioning and viewport fit at 320 pixels, and emulate reduced motion to confirm entry animation is disabled without hiding the feedback.

Truck UI and its API/types helpers are grouped under `frontend/src/pages/trucks/`. Shared pagination is under `frontend/src/components/table-pagination.tsx` and takes page/pageSize/total/state/callback without truck request logic.

Use browser developer tools to inspect and temporarily interrupt requests on this disposable environment. Restore connectivity after each scenario:

- Throttle the list request, change page/filter while an earlier request is delayed, and confirm only the latest items, total and page appear. Navigation is disabled while loading; there is no flash of stale results.
- Block `/api/trucks*` and change a filter: expect the list error and disabled pagination. Unblock and choose `Bandyti dar kartą`; the current query succeeds.
- Block mutation requests before saving/deleting. Expect preserved form values or confirmation context and a concise Lithuanian error. Unblock and retry successfully. While a request is pending, repeated clicks/Enter must not issue duplicate mutations.
- Let POST/PATCH/DELETE succeed, then block only its subsequent list GET or `/api/trucks/stats` GET. The dialog closes; a save's success toast (or deletion's existing notice) is shown alongside the appropriate list/statistics refresh error. A successful save does not become an error toast because a read failed, and its toast may dismiss normally while the read error remains actionable. Retrying the failed read must not repeat the mutation, emit another save toast or refetch the other successful read. Developer tools' request breakpoints or a temporary local request interceptor can distinguish methods; no application changes are necessary.
- Retire a truck from a second client while its editor is open. Saving returns the missing/deleted message; refresh or dismiss it to recover, without reviving the truck.

## Historical preservation

Before retiring referenced truck 1 in the UI, capture the fixture records from the repository root:

```bash
docker exec viptop-truck-ui-db psql -X -A -t -U viptop -d viptop_truck_verify \
  -c 'SELECT row_to_json(r) FROM routes r ORDER BY id; SELECT row_to_json(s) FROM route_stops s ORDER BY id; SELECT row_to_json(e) FROM service_events e ORDER BY id; SELECT row_to_json(b) FROM bins b ORDER BY id' \
  > /tmp/viptop-truck-history-before.txt
```

Delete `Šiukšliavežė 01` through confirmation. Run the same command with output `/tmp/viptop-truck-history-after.txt`, then `diff -u /tmp/viptop-truck-history-before.txt /tmp/viptop-truck-history-after.txt`: expect no differences. Inspect the retained truck and historical attribution:

```sql
SELECT id, name, max_bins_per_trip, available, deleted FROM trucks WHERE id=1;
SELECT e.id, e.bin_id, e.service_ts, e.fill_level, e.duration,
       r.id AS route_id, r.service_date, r.status,
       t.id AS truck_id, t.name, t.deleted
FROM service_events e
JOIN routes r ON r.id=e.route_id
JOIN trucks t ON t.id=r.truck_id
ORDER BY e.id;
```

Truck 1 keeps its ID/name/capacity and now has available false/deleted true. Every reference/value in the captured collection records remains unchanged; the joins still resolve the retained truck. GET `/trucks` excludes it, GET `/trucks/1` and PATCH `/trucks/1` return `404`. Future history screens must use this join rather than the management detail endpoint.

## Packaged startup, persistence and cleanup

On a separate disposable Compose project, use a temporary env file with the example connection settings and the unreachable GIS URL above. Keep operational `.env` and storage untouched. If standard ports are occupied, use an override file changing all three published ports. To verify packaged files, reset the frontend/backend bind mounts to `[]` in that override; environment settings supply the database connection. Compose automatically sets `VIPTOP_API_PROXY_TARGET=http://backend:8000`.

```bash
docker compose --env-file /tmp/viptop-truck-ui.env -p viptop-truck-ui-verify config --quiet
docker compose --env-file /tmp/viptop-truck-ui.env -p viptop-truck-ui-verify up --build -d
docker compose --env-file /tmp/viptop-truck-ui.env -p viptop-truck-ui-verify logs backend
docker compose --env-file /tmp/viptop-truck-ui.env -p viptop-truck-ui-verify exec backend \
  ls alembic/versions/0003_truck_retirement.py
```

Add `-f docker-compose.yml -f /tmp/viptop-truck-ui-compose.yml` before the action in every command when using an override. Logs must show migration through `0003` before application startup. Load the container frontend, create/edit trucks, and repeat two-page navigation/filters/deletion against a 21-truck synthetic fleet. SQL `generate_series` as above can prepare it, omitting history inserts and using the Compose database's name. IDs continue after any earlier fixture operations; find rows by their synthetic names.

Record a committed edited row and the retired row's flags. Restart only the backend with `docker compose ... restart backend`, reload the browser, and compare API/SQL values. They must persist; startup/shutdown is normal with no GIS requests. Run `docker compose ... exec backend uv run alembic check` for schema agreement.

After recording results, stop native backend/frontend/preview processes, run `docker compose ... down --volumes` for the owned disposable project, and remove `viptop-truck-ui-db`. Remove owned temporary env/override/snapshot files. Do not remove unrelated containers, databases, volumes or images.

## Recorded initial-slice results — 2026-10-08 (twenty-row baseline)

Verification used disposable PostgreSQL 17 databases and a separate Compose project through rootless Podman, because the local Docker daemon was inaccessible. The packaged frontend/backend had no source bind mounts. All fixture records were synthetic.

- Empty/populated upgrade, repeated upgrade, Alembic schema comparison, incompatible-data rollback and guarded downgrade passed. Database constraints also rejected Unicode whitespace-only names consistently with API trimming.
- API pagination (20/1), filtered totals, Lithuanian/literal substring matching, strict mutation validation, partial/empty updates, missing/deleted exclusions, concurrent retirement and controlled persistence rollback passed.
- Native development, built preview and packaged Compose proxies/deep links worked. Desktop and 320-pixel browser checks covered navigation, filters, pagination, CRUD, form resets, keyboard operation, confirmation focus and focus restoration.
- Delayed responses, interrupted CRUD/list requests, retries and committed mutation followed by failed list refresh preserved the intended state. Last-page deletion recovered correctly; CRUD caused no full-page navigation.
- UI retirement of the referenced truck preserved complete Bin/Route/RouteStop/ServiceEvent snapshots. Historical joins retained truck attribution; list/detail/edit excluded the truck and its flags became deleted true/available false.
- Frontend lint/build, focused backend Ruff checks, Compose configuration validation and packaged Alembic schema comparison passed. Committed edits survived backend restart and browser reload; packaged startup applied `0003` before serving with no GIS import.
- Native shutdown completed normally. Owned verification containers, volumes, images, server processes and temporary fixtures/settings were removed after verification; operational storage was not used.

## Recorded refinement results — 2026-10-08 (ten-row version)

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

## Recorded presentation results — 2026-10-08 (save toasts and mobile navigation)

Verification used native FastAPI against a separate disposable PostgreSQL 17 container and both Vite development and the rebuilt preview. The initial synthetic fleet had 27 trucks with capacities 1–27 and 24 available, producing `24 iš 27` and 89%. No operational data/settings were used. The in-app browser was unavailable; standalone Chromium checks and visual screenshot inspection covered the running system.

- Add/clear had equal measured width/height and matching font/padding, with the filled clear background retained, at 320/639/640/1440 pixels. Total, average and available/total counts shared their font size/weight; wrapping avoided horizontal overflow. The true empty fleet rendered 0/—/0%, `0 iš 0`, the neutral circle and usable equal actions.
- Mobile menu checks passed initially hidden links, keyboard opening/selection, closed-link exclusion from Tab order, Escape focus restoration, active navigation, 639/640-pixel transitions and deep-link reload. Desktop links remained directly visible.
- Real create/edit saves produced top-right success toasts without inline save-success text, preserved page/filter context and refreshed the list/overview. Client validation sent no mutation; a real backend 422 response retained field errors and produced a sanitized error toast. Interrupted saves preserved input/focus, kept the editor open and succeeded on retry. Repeated Enter during a delayed save issued one mutation.
- Error toasts remained visible and accessible above the editor. Close/Escape dismissed feedback without closing the editor; accessible error announcements were not hidden by the modal. Reduced-motion checks disabled entry animation. Automatic dismissal passed after previous manual dismissals; focus restoration also resumed the shared timer rather than leaving later toasts permanently paused.
- A committed save followed by controlled list or statistics read failure kept successful feedback and the separate read error. Each retry issued only its failed GET, with no repeated mutation, duplicate toast or unrelated overview/list fetch. The complete browser run reported no JavaScript errors or mutation-driven document reloads.
- Rebuilt preview passed direct navigation/reload, mobile menu, real create with a reduced-motion toast, retirement and return to the true empty overview/list, page 1 and logical add-button focus. Desktop and mobile screenshots were inspected.
- Frontend lint/build, strict OpenSpec validation and whitespace checks passed. No automated test files were added. Previously recorded storage/backend checks remain applicable; this presentation refinement required no backend or migration changes.
- Native backend shutdown completed normally; owned frontend/preview processes, disposable database container/storage and temporary verification scripts/screenshots were removed after recording results.
