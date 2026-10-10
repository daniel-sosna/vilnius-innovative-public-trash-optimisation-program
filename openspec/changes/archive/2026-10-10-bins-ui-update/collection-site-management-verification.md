# Collection-site management verification

Use a disposable PostgreSQL database for migration/rollback fixtures, forced
failures and deletion checks. Export its `DATABASE_URL` with the existing
`postgresql+psycopg` driver before running commands from `backend/`. Do not use
the imported registry as a deletion fixture. No VASA command or source request
is needed. The earlier browsing guide remains a GET-only procedure.

## Schema and migration

```bash
uv run alembic upgrade head
uv run alembic check
uv run alembic current
```

On a disposable database at `0012`, retain representative Site/Bin/history,
resident-request, truck and import-bookkeeping rows. Compare all columns and
generated IDs before and after upgrade to `0013`; no row should change. These
read-only queries identify the new contract:

```sql
SELECT column_name, is_nullable FROM information_schema.columns
WHERE table_name='bins' ORDER BY ordinal_position;
SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint
WHERE conrelid='bins'::regclass ORDER BY conname;
SELECT count(*) FROM bins WHERE external_id IS NULL;
SELECT version_num FROM alembic_version;
```

Within a disposable transaction, insert two Bins with NULL external IDs under
one Site; both must succeed. A repeated known external ID must fail uniqueness.
Delete a Site containing history and resident requests, inspect that its
descendants disappeared, then ROLLBACK and inspect that all rows returned.
Unrelated Site/Bin/truck rows must survive.

```bash
# First, only when no NULL external IDs exist in disposable storage:
uv run alembic downgrade 0012
uv run alembic upgrade head
# After creating a manual Bin, this must fail without changing rows or schema:
uv run alembic downgrade 0012
```

The downgrade locks Bins before checking NULL identities. It never deletes
manual records or fabricates an external ID to make rollback possible.

## Local cleanup compatibility

Use local disposable records only. An unseen imported Bin inside the bounds
must be a candidate; NULL-external-ID Bins must not be. The affected-Site query
and delete predicate both include the explicit non-NULL guard:

```sql
SELECT DISTINCT site_id FROM bins
WHERE external_id IS NOT NULL
  AND longitude BETWEEN 24.98 AND 25.52
  AND latitude BETWEEN 54.55 AND 54.85
  AND NOT EXISTS (
    SELECT 1 FROM vasa_import_progress p
    WHERE p.run_id=1 AND p.kind='seen' AND p.complete
      AND p.work_key=bins.external_id::text
  );
```

A manual-only Site must not enter the affected set merely because its Bins
have no source identity. When a shared imported Site loses its imported Bins,
a remaining manual Bin still prevents empty-Site removal.

## Recorded evidence

The revision numbers in the historical evidence below refer to the branch
before merging main. Resident requests now use `0010`, and manual collection
management now uses `0013`; follow the current commands above for verification.

After merging main on 2026-10-10, disposable PostgreSQL 16.2 verification
confirmed a single `0013` head, fresh and repeated upgrades, no Alembic schema
drift, compatible downgrade/re-upgrade and refusal to downgrade manual Bins.
Real HTTP requests verified volume-based Trucks with landfill assignment,
Site creation, Bin addition/listing and resident requests. Synthetic collection
CSV exports imported successfully twice. Site deletion cascaded through history,
requests, schedules, population allocation and bin days while retaining Trucks.
Manual-only storage was excluded from VASA schedule retrieval without source
requests. Frontend lint/build and OpenSpec validation passed; validation retains
its requirement-length warnings. The disposable database was removed afterward.
Docker socket access was denied, so the Compose database reset was not performed.

On 2026-10-10, native disposable PostgreSQL 16.2 at revision `0005` was populated
with a Site, an imported Bin with nullable metadata, history, a resident request,
a truck and an import run. Upgrade preserved every row and ID. `alembic check`
reported no new operations. Multiple NULL identities were accepted; duplicate
known identity was rejected. Cascading Site deletion and transaction rollback
were verified. Compatible downgrade/re-upgrade preserved fixture rows, while
downgrade with manual Bins failed and retained revision `0006` and CASCADE.
Local affected-Site selection excluded a manual-only Site and still selected
the unseen imported fixture. Docker API access was unavailable; the installed
application's PostgreSQL volume was not modified.

## Create a Site and initial Bins

Point `API` at a backend configured with **disposable** `DATABASE_URL`. Native
verification used `http://127.0.0.1:18006`, with the frontend on 18007 proxying
there and the configured OpenFreeMap Liberty style. Existing Compose storage
was not used as a mutation fixture.

```bash
API=http://127.0.0.1:18006
cat > /tmp/manual-site.json <<'JSON'
{"street":"Didlaukio g.","sub_district":"Verkių sen.","house_number":"53A","postal_code":"08303","latitude":54.72,"longitude":25.28,"bins":[{"object_group":"Gyventojai","capacity_m3":1.1,"waste_carrier":"Ecoservice","inventory_number":"MANUAL-1","waste_type":"Glass waste"},{"object_group":"Įstaiga","capacity_m3":2.25,"waste_carrier":"Kauno švara","inventory_number":"MANUAL-2","waste_type":"Paper/plastic waste"}]}
JSON
curl --fail-with-body -i -H 'Content-Type: application/json' \
  --data-binary @/tmp/manual-site.json "$API/sites"
```

Expect 201 `{id,address,bin_count:2}`. Substitute its ID below. Repeating the
payload must create a distinct generated ID and `manual:<UUID>` key, even though
the address matches. Postal code retains `08303`; blank/NULL/omitted stores NULL.
All five Bin fields are required; capacities must be positive finite JSON
numbers (not strings/booleans). `1.1abc`, 0, negative/nonfinite values, unlisted
waste/carriers, extra assigned fields and an empty `bins` array produce 422.

```sql
SELECT id,site_key,address,latitude,longitude FROM sites WHERE id=:site_id;
SELECT id,site_id,external_id,street,sub_district,house_number,postal_code,
 latitude,longitude,capacity_m3,district,region,city,territory_type,client_count
FROM bins WHERE site_id=:site_id ORDER BY id;
```

Coordinates/address must be copied to every child, fixed Vilnius metadata must
match README, and identities/territory/client counts must be NULL. No history or
resident request is generated. Numeric 1.1 is stored without presentation rounding.

To demonstrate persistence rollback, on disposable storage install this temporary
trigger, record Site/Bin counts, POST the payload, inspect generic 500 and unchanged
counts, then remove the trigger/function. Never install it on the actual registry.

```sql
CREATE FUNCTION verification_reject_bin() RETURNS trigger LANGUAGE plpgsql AS
$$ BEGIN RAISE EXCEPTION 'controlled verification'; END $$;
CREATE TRIGGER verification_reject_bin BEFORE INSERT ON bins
FOR EACH ROW EXECUTE FUNCTION verification_reject_bin();
-- POST /sites now fails; compare Site/Bin counts to before the request.
DROP TRIGGER verification_reject_bin ON bins;
DROP FUNCTION verification_reject_bin();
```

Creation evidence on 2026-10-10: the real disposable backend returned two-Bin
201 summaries; SQL confirmed copied coordinates/text, metadata, NULL identities
and independent keys at repeated addresses. The forced insert failure returned
`{"detail":"Collection operation failed"}` and left no partial Site/Bin rows.
The configured frontend passed desktop 1280×900 and 320×640 browser checks:
scrollable modal with no horizontal overflow, stable dynamic Bin forms, final
form removal disabled, no initial marker, one moving click-selected marker,
keyboard pan plus explicit center selection, malformed capacity rejection,
JSON numeric decimals, empty optional postal code, retained inputs after failed
POST, disabled pending submit and a single successful POST, preserved address
filter, list refresh without document reload and cancel focus restoration.

## Add a Bin

Create `/tmp/manual-bin.json` containing just one object from the `bins` array
above, then use the created Site's ID:

```bash
SITE_ID=123 # replace with the disposable Site's returned ID
curl --fail-with-body -i -H 'Content-Type: application/json' \
  --data-binary @/tmp/manual-bin.json "$API/sites/$SITE_ID/bins"
curl --fail-with-body "$API/sites/$SITE_ID"
curl --fail-with-body "$API/sites/$SITE_ID/bins?page=1"
```

Expect 201 `{id,inventory_number,waste_type,capacity_m3}`. SQL inspection must
show NULL external identity/client count/territory and fixed Vilnius metadata.
The new Bin's coordinates equal the stored Site coordinates; the Site marker
stays fixed. Address inheritance takes `street`, `sub_district`, `house_number`
and `postal_code` from the same lowest internal Bin ID, with NULLs preserved.
Verify with a representative imported fixture whose first child has NULL
sub-district/postal code and second has known values. Repeat with a legacy empty
Site: all four inherited fields remain NULL. No parsing of display address occurs.
Positive nonexistent/overflow IDs return 404; `0`, `-1`, `abc`, `1.1` return 422.

Addition evidence on 2026-10-10: API/SQL checks passed for manual, representative
imported and legacy empty disposable Sites, including NULL inheritance, fixed
metadata, Site coordinate copying and exact numeric 1.125. Missing/invalid/oversized
IDs returned 404/422. Browser checks used a >10-child imported fixture and a manual
Site to verify the five-field modal, cancel focus, failed POST retaining values,
refreshed Site statistics, automatic navigation to the newest Bin's page and
normal empty-history/focus restoration. Frontend lint/build passed after this slice.

## Hard deletion, rollback and concurrent membership

Use IDs from disposable fixtures only:

```bash
BIN_ID=456 # replace with a disposable Bin ID
curl --fail-with-body -i -X DELETE "$API/bins/$BIN_ID"
# 200 {"site_id":123,"site_deleted":false}; true for the final Bin.
curl --fail-with-body -i -X DELETE "$API/sites/$SITE_ID"
# 204, no body. Repeating after removal returns 404.
```

Before deleting, insert one synthetic history and resident request per fixture
Bin, retain unrelated Site/Bin/history/request rows, and record counts/coordinates.
Delete a Bin under a Site with >10 children: the Site must survive even when other
children are off-page, coordinates stay fixed, and only its dependents disappear.
Delete a Site: every attached Bin/history/request disappears. Delete a sole Bin:
Site and dependents disappear together. Confirm unrelated rows remain intact.

```sql
INSERT INTO bin_hist(bin_id,date,was_serviced,fill_level)
VALUES (:bin_id,'2026-10-10 09:00',TRUE,0);
INSERT INTO resident_requests(bin_id) VALUES (:bin_id);
SELECT id,latitude,longitude FROM sites WHERE id=:site_id;
SELECT count(*) FROM bins WHERE site_id=:site_id;
SELECT count(*) FROM bin_hist WHERE bin_id=:bin_id;
SELECT count(*) FROM resident_requests WHERE bin_id=:bin_id;
```

Use the creation rollback function pattern with a `BEFORE DELETE ON sites`
trigger that raises an exception. Both Site DELETE and sole-Bin DELETE must
return generic 500 and retain Site/Bin/history/request rows. Remove the temporary
trigger/function afterward. Nonexistent/overflow positive IDs return 404; invalid
IDs return 422 for both endpoints.

To reproduce serialized membership on disposable PostgreSQL, use controlled
sessions and finish within the configured one-second lock timeout:

1. Hold `SELECT id FROM sites WHERE id=:site_id FOR UPDATE` for a two-child
   fixture in session A. Start HTTP Bin DELETE for each child in two other
   sessions, observe lock waiting in `pg_stat_activity`, then commit A. Both
   deletions succeed; exactly one reports `site_deleted=true`; no Site remains.
2. Lock a one-child Site in session A. Start an HTTP final-Bin DELETE in B and
   observe its lock wait. Invoke `app.services.sites.add_bin` using A's SQLAlchemy
   Session with a valid Bin definition (it commits). B deletes the original Bin
   with `site_deleted=false`; Site and added Bin survive.
3. Lock another one-child Site in A. Start HTTP Bin addition in B and observe its
   lock wait. Invoke `app.services.bins.delete_bin` using A's Session (it commits).
   B returns 404; no Site or detached Bin survives.

Deletion/concurrency evidence on 2026-10-10: disposable API/SQL checks passed for
11-child nonfinal deletion, 204 Site cascade, 200 final-Bin outcome, history and
resident-request removal, unchanged surviving Site coordinates, unrelated fixture
preservation, forced transaction rollback and all 404/422 identity cases. Controlled
sessions observed PostgreSQL lock waiting and passed all three sequences above.
The two DELETE responses were 200 with one false and one true outcome.

Browser evidence: independent red row actions opened confirmation without Site
navigation/history, cancel started focused and restored trigger focus, Lithuanian
consequence text included dependent records and final-Site removal, pending controls
prevented repeated requests, a failed DELETE retained confirmation and allowed retry,
filtered Site page 2 recovered to page 1, Bin page 2 recovered after its only row was
removed, and final-Bin deletion navigated to a refreshed Site list. A real 404 after
an external fixture deletion offered read refresh without replay. At 320×640 the
list, Bin rows and confirmation had no page overflow.

## Complete-flow and final checks

The remaining browser checks on 2026-10-10 held obsolete Site and Bin GET responses
until after current filter/membership refreshes. Late reads did not replace fresh
rows or counts. A successful Site DELETE followed by failing list/overview reads
and a successful Bin DELETE followed by a failing Site-statistics read retained
the committed outcome; retry controls sent GET only, never another DELETE.
The public resident page retained its static/nonselecting map at 320px, submitted
a disposable request successfully, and showed its missing state after Site deletion.
Creation retry after a forced map-style failure retained address values and cleanup
removed the map on dialog close. Existing Site map clicks did not select/move the
marker. Desktop and 320px list/detail/add-Bin/confirmation layouts were inspected.
All complete management flows used the same configured frontend API proxy and
native disposable backend, with real PostgreSQL persistence and external map style.

```bash
cd frontend
npm run lint
npm run build
cd ../backend
uv run python -m compileall -q app alembic/versions/0013_manual_collection_management.py
# Export disposable DATABASE_URL before either Alembic command.
uv run alembic upgrade head
uv run alembic check
cd ..
openspec validate bins-ui-update --strict
git diff --check
```

Results: frontend lint/build passed (Vite retained its bundle-size advisory),
Python syntax checks passed, revision was `0006 (head)`, Alembic reported
`No new upgrade operations detected`, and strict OpenSpec validation passed.
No automated test suite or application dependencies were added; no VASA request,
import rerun, unrelated refactor or existing-storage reset was performed. Temporary
verification scripts/fixtures/screenshots were kept outside the repository.
Docker API access remained denied, so Compose rebuild/activation was not exercised;
verification used the configured native application rather than claiming Docker
execution. Existing PostgreSQL volume data was not modified for verification.

Final focused checks also confirmed a real missing-Site response during Bin addition:
entered values remained, save was disabled, focus moved to cancel, and navigation
back to the list worked. Missing deletion similarly focused an enabled cancel
control. Final 320px/desktop screenshots confirmed aligned Site headings/actions
and reachable modal controls after those adjustments.

## Requested UI refinements

On 2026-10-10 the Truck row delete control was extracted into `RowDeleteButton`
and reused for Trucks, Sites and Bins. Browser checks confirmed matching ghost
variants, red text/hover styling, independent row activation and cancel focus.
The Site add action now aligns vertically with the search input on desktop and
wraps responsively at 320px. Site rows display `Didlaukio g. 53A` while search
for `08303` still finds the full stored address; confirmations/details/API keep
that full value.

The creation modal has the requested map title and initially empty, read-only
`Platuma (lat)` / `Ilguma (lon)` fields directly after house number/postal code.
Two different map clicks updated the fields and moved a single marker. The
previous below-map helper text, center-selection button and selected-coordinate
status were removed. On the focused map, arrow-key movement followed by Enter
or Space selected the center without submitting the form. The shortcut is
explained accessibly on the canvas. Forced map failure/retry retained the address,
and submitted coordinates matched the read-only values. Screenshots at 1280×900
and 320×640 confirmed field placement, reachable controls and no page/modal
overflow. Frontend lint/build and strict OpenSpec validation passed.

The subsequent coordinate-display refinement moved both inputs immediately below
the map and made them disabled, muted, nonfocusable and nonselectable. Focus attempts
failed; computed pointer interaction was `none` and user selection was `none`.
At desktop/320px widths, empty fields populated after a map click, a second click
updated the values and the sole marker, and the modal had no horizontal overflow.
Frontend lint/build and strict OpenSpec validation passed again.
