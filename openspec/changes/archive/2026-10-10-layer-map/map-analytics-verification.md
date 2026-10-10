# Map analytics verification

Landfill change status (2026-10-10): manual verification accepted by the developer;
all 17 `layer-map` tasks closed with their authorization. Earlier pending statuses
below are historical. The separate `layer-map-bins` implementation and verification
record follows at the end; prior acceptance does not cover that change.

Bin change status (2026-10-10): the developer reports that all functionality has
been checked and verified and explicitly authorizes completing every remaining
task, syncing the specs and archiving `layer-map-bins`. All 21 tasks are closed
on that acceptance and the recorded technical checks. Earlier pending bin
statuses below are historical.

Run these reads against the existing landfill catalog. Do not import, reseed,
migrate or change landfill records for this verification. The expected three records come
from migration `0006`; nullable columns follow `0007`.

## Read-only API check

From the repository root, with the backend already running:

```bash
MAP_API_URL=http://127.0.0.1:8000 python - <<'PY'
import json, os, urllib.request
base = os.environ['MAP_API_URL'].rstrip('/')
def read(path):
    with urllib.request.urlopen(base + path, timeout=10) as response:
        assert response.status == 200
        return json.load(response)
geo = read('/map-analytics/landfills')
catalog = read('/landfills')
expected = {1: [25.1563, 54.6567], 2: [25.135007, 54.652436],
            3: [25.1583394, 54.6669658]}
assert geo['type'] == 'FeatureCollection'
assert [f['id'] for f in geo['features']] == list(expected)
assert [r['id'] for r in catalog] == list(expected)
for feature, row in zip(geo['features'], catalog, strict=True):
    assert feature['type'] == 'Feature'
    assert feature['geometry'] == {
        'type': 'Point', 'coordinates': expected[feature['id']]}
    assert set(feature['properties']) == {
        'name', 'operator', 'address', 'coordinate_quality'}
    assert feature['properties'] == {
        key: row[key] for key in feature['properties']}
    assert set(row) == {
        'id', 'source_id', 'dataset_name', 'dataset_description', 'latitude',
        'longitude', 'name', 'operator', 'address', 'facility_role', 'waste_streams',
        'status', 'coordinate_quality', 'coordinate_source', 'facility_source',
        'municipal_arrangement_source', 'current_status_source', 'verified_at'}
print('PASS: three seeded points, coordinates, exact properties and catalog contract')
PY
```

Exit 0 and `PASS` indicate success. HTTP/network failures, invalid JSON or failed
assertions exit nonzero. Change only `MAP_API_URL` for a different backend port.
The browser equivalent is `/api/map-analytics/landfills` through Vite's proxy.

The projection selects only the seven required columns in ascending ID order.
It skips a row if either coordinate is null, retains null properties and returns
`features: []` for no displayable rows. The endpoint uses `CollectionSession`:
short PostgreSQL repeatable-read/read-only transaction, timeouts and rollback.
These branches can be inspected without altering real catalog data.

## Recorded results

2026-10-10: baseline integrated by fast-forward to `db3ce5f`. API check passed
against this checkout's backend on port 18008 and existing PostgreSQL on 5432:
IDs 1–3, exact stored coordinates, four detail properties, unchanged 18-field
catalog response. No storage writes, import, reseeding or new migrations.

## Browser walkthrough: three real facilities

Start this checkout's backend and frontend with the same database connection.
Set `VITE_MAP_STYLE_URL` at frontend startup/build time and point
`VIPTOP_API_PROXY_TARGET` at that backend. For the current native session, the
frontend is `http://127.0.0.1:18009` and its backend is port 18008.

1. Navigate from trucks using `Žemėlapio analitika`. Confirm the link is active,
   the screen belongs to the shared admin layout and both `Sąvartynai` and
   `Konteineriai` are offered. Follow the bin walkthrough below for that layer.
   Open `/admin/map-analytics` directly, refresh, and use Back/Forward.
2. The large Vilnius-centered map fills the content width. One card underneath
   shows `Sluoksniai`, name-only checkboxes, then `Legenda` and color labels. Pan,
   use wheel/touch zoom, focus the map and use arrow keys and +/-; verify labeled
   `Priartinti` and `Atitolinti` controls. The layer starts unchecked.
3. In browser Network tools filter `map-analytics/landfills`: no initial read.
   Check `Sąvartynai`: exactly one GET through `/api`, then its real features.
4. Pan southwest toward Gariūnai/Lentvario streets (around 25.15, 54.66). Zoom
   out to about 10 to group nearby facilities; each displayed count must match
   its represented records, with all groups/individuals totaling 3. Click a
   cluster: it expands toward its members and opens no facility popup. Zoom in
   until three individual circles appear (zoom 15 guarantees no clustering),
   then zoom back out and verify regrouping. Exact intermediate split depends
   on zoom; it never changes the underlying three records.
5. Click each individual marker. Verify the facility-name heading and only the
   `Operatorius` and `Adresas` detail rows, with no `Pavadinimas` or
   `Koordinačių tikslumas` rows, the correct facility
   and Lithuanian presentation below. Closing is labeled `Uždaryti informaciją`;
   Escape closes the popup and returns focus to the map. Known descriptions use
   Lithuanian; nulls display `N/A` (inspect the presenter without modifying the
   three real records). Unknown source text remains faithful.

| ID | Expected heading | Operator | Address |
| --- | --- | --- | --- |
| 1 | Ecoservice Gariūnų atliekų priėmimo ir rūšiavimo aikštelė | UAB Ecoservice | Gariūnų g. 71, Vilnius, Lietuva |
| 2 | Ekobazės Lentvario atliekų tvarkymo aikštelė | UAB Ekobazė | Lentvario g. 13A, Vilnius, Lietuva |
| 3 | Vilniaus regiono mechaninio biologinio atliekų apdorojimo įrenginiai (MBA) | VAATC įrenginiai; dabartinę veiklos tvarką reikia patvirtinti | Jočionių g. 13, Vilnius, Lietuva |

These are recorded locations, not surveyed entrances or an assessment of current
intake capacity. Coordinate quality stays in the API but is not displayed in the
compact popup. The `Legenda` section in the card under the map displays a black
`Sąvartynai` swatch matching the pins and clusters. It lists all registered color
meanings even while their layer is unchecked.

## Cache, failures, camera and mobile

- Uncheck while a popup is open: all three style layers and the popup disappear.
  Recheck: the points return and Network shows no second successful read. Pan
  and zoom first; repeat fast toggles without any center or
  zoom reset, recreated canvas, or basemap reload.
- Delay the first GET in browser tools. Toggle off/on before completing it:
  exactly one request is shared. Complete it while unchecked: no features show.
  Re-enable: cached data displays without another read. Navigate away with a
  pending read: it is aborted and cannot update the old page.
- Fail only the dataset request using browser tools, preserving map resources.
  See `Nepavyko įkelti sluoksnio.` and its retry. Basemap pan/zoom still works.
  Restore access and retry: only this dataset reads again and the camera stays
  fixed. Override this GET with a successful empty FeatureCollection to verify
  `Duomenų nėra.` separately from loading/error; never mutate the database.
- Fail the configured style/tile/glyph request. See the map-specific error and
  `Bandyti dar kartą`. Restore access and recover: the camera, selected IDs and
  cached dataset return without a landfill refetch. Restart frontend with a
  missing or invalid style setting: it identifies the configuration issue in
  Lithuanian. A valid alternative style is used without a component change.
- At 320px the navbar opens/closes through its labeled button; the shared card
  stays below the map with both sections visible. Use Tab, Space and Enter
  for the checkbox/zoom/retry/close controls. Clicking/touching the map should
  not draw a canvas outline; keyboard interaction should show visible focus. Confirm
  readable popup contents with internal scrolling and no page-wide horizontal
  scrolling. Repeat at desktop width. Resizing never resets the camera.
- Revisit trucks, sites and an existing site detail. Verify navigation, refresh,
  lists and the site's location map. Use existing collection records only.

## Extending the registry

`frontend/src/pages/map-analytics/layers.ts` exports the registry `mapLayers` and
`getActiveLayers(selection)`. The latter resolves stable selected IDs to full
metadata, including `meaning`, independently of localized labels. The page's
`data-active-layers` also records selected IDs. Successful GeoJSON stays keyed
by ID in the page session; no assistant-specific API or global cache is added.

To add a point dataset, export a definition built with `createPointLayer` from
`components/maps/point-layer.ts`, supplying a unique stable ID, label, meaning,
abortable `load`, appearance, `legend: [{ label, color }, ...]` and a DOM detail presenter. Feature IDs must be
unique within the dataset. Add it to `mapLayers`. The helper supplies independent
namespaced sources, cluster circles/counts/individual circles, expansion,
visibility and cleanup. Defaults are `clusterRadius: 50`, `clusterMaxZoom: 14`;
`appearance.countFont` is adjustable and must exist in the configured style's
glyph provider (the default provider supports `Noto Sans Regular`). Use safe
DOM/text content rather than inserting source strings as HTML.

Point `appearance.color` can be a constant or a native MapLibre property-based
color expression. For a categorized dataset, supply one labeled legend
entry per category and a uniform `appearance.clusterColor` for grouped points
(with its own legend entry if it differs). Bins supply these category and group
entries through the shared category module.

A future non-point definition implements `MapLayerDefinition` directly: set its
render `kind` and geometry-independent legend entries, load a GeoJSON
FeatureCollection of its geometry, and implement
`attach(context, data)` returning `setVisible(boolean)` and `dispose()`. Attach
runs after style readiness; the renderer owns sources, style layers and events,
changes visibility without moving the camera, and removes everything on dispose.
`context.showDetails(id, coordinates, content, onClose?)` and `closeDetails(id)` provide
shared popup ownership if needed. This boundary never calls a polygon a marker
or applies point clustering to it. Recovery attaches a new renderer against
retained cache; disposal must tolerate in-flight interaction completion.
No non-point renderer is delivered in this change.

Renderers may optionally implement `setData(data)`; the map updates an attached
renderer only when its rendered collection reference changes. Point-source
updates preserve attachment and camera, refresh original-feature lookup and
gate interactions until the latest source update and tiles are ready. Optional
`clustering` and `overlapGroup` point-definition settings are used by bins;
landfills keep the defaults above. Bin clustering derives its maximum from the
map and reserves a higher source zoom (22/23 currently), capped at the installed
MapLibre canonical tile limit of 25. The subsequent collision fix uses that
native index directly for bins and one unclustered display source; landfills
continue to use native source clustering. See the collision verification below.

## Temporary simultaneous-point verification (historical `layer-map` walkthrough)

For browser acceptance only, temporarily create a second definition next to
`landfillsLayer` using `createPointLayer` with ID `landfills-verification`, label
`Patikros sluoksnis`, a distinct color with a matching `legend` entry, `loadLandfills` and `landfillDetails`.
Register both in `mapLayers`. Its loader reads the same existing three facilities;
do not add database records or a second shipped dataset.

Enable both and inspect each independent namespaced GeoJSON source and count
layers in browser development tools. Each has only three records, never a
combined count of six. Delay/fail only one layer's loader and verify the other
stays usable; toggles, retry and loading belong to their ID. Activate the topmost
point/cluster, hide that definition and activate the other: details/expansion
belong to the visible dataset. Remove the temporary definition and registry entry
before delivery, then confirm the selector again contains only `Sąvartynai`.

## Acceptance status and environment limits

2026-10-10: `npm run build` and `npm run lint` passed. Build reports its existing
large-bundle advisory; no new dependencies or automated test suite were added.
The configured Liberty style declares `Noto Sans Regular`. Vite serves the deep
link directly. Code inspection confirms independent source IDs, generic renderer
lifecycle, null-preserving DOM presentation, visibility-driven popup cleanup,
abortable pending reads and separate camera/cache lifetimes.

Browser execution is **pending**, including real cluster clicks, popup display,
network timing, recovery, keyboard/mobile layout, existing-page regressions and
the temporary simultaneous-layer walkthrough. The browser runtime reported no
available browsers; build or HTTP reads do not establish these UI behaviors.
Keep their OpenSpec checkboxes open until the walkthrough is actually performed.

On resuming, read-only inspection again confirmed that the existing PostgreSQL
database contains `landfills`. Pending cluster expansion is invalidated by a
visibility change, including switching off and on before the worker responds.
Build and lint passed again after that fix. The documented API command passed
both directly on port 18008 and through Vite's `/api` proxy on port 18009.
HTTP reads of the analytics deep link and its transformed modules succeeded.

OpenSpec acceptance progress is 6/15. Tasks 1.1, 2.1–2.3, 3.2 and 4.4 are
complete. Application code and walkthrough documentation are implemented for
the remaining tasks; their required browser verification is still pending.
The temporary second dataset has not been registered or verified yet; the
delivered registry contains only `Sąvartynai`.

Collection-page regression checks require the CSV exports named in `AGENTS.md`:
`sites_<digits>.csv`, `bins_<digits>.csv` and `bin_hist_<digits>.csv` under
`backend/data/`. This prerequisite is now satisfied (see the results below).
The files are ignored by Git; use `rg --files --hidden --no-ignore backend/data`
or a filesystem glob to check their presence.

## Main integration verification

2026-10-10: stashed tracked and untracked analytics work, fetched `origin/main`
and fast-forwarded `layer-map` to `a495c12`. Restoring the stash conflicted only
in README additions; both collection-site management and analytics sections
were retained. All 20 untracked files were restored byte-for-byte, the restored
tracked changes were reconciled with main, and the temporary stash was dropped.

After integration, `npm run build`, `npm run lint`, `git diff --check` and
`openspec validate layer-map --strict` passed. The merged app's OpenAPI includes
both collection-site mutation routes and `/map-analytics/landfills`. The documented
real API check passed directly and through Vite's proxy; the analytics deep link
returned the frontend entry page. Existing PostgreSQL reports migration revision
`0013` and contains the landfill table. Main's CSV importer and migration chain
were retained; no data needed dropping and no import or migration was performed.

Browser acceptance remains pending because the browser connection is still
unavailable. OpenSpec progress remains 6/15.

## Collection exports and container verification

2026-10-10: the supplied exports are present and services on ports 8000/5173
respond. The Docker socket remains inaccessible to this agent, but direct HTTP
and PostgreSQL connections work. Container `/map-analytics/landfills`,
`/landfills` and the equivalent `/api` proxy routes return HTTP 200.

The collection tables initially contained zero records. Following the project's
development-data instructions, ran its existing importer once against PostgreSQL:

```bash
cd backend
# Use the existing accessible DATABASE_URL and required settings.
uv run python -m app.interfaces.table_import
```

This was development collection setup, separate from the read-only landfill API
checks. No landfill file was selected, and the complete `/landfills` response
was identical before and after the import. No migrations or new importer code.

| Table | Supplied export | Imported rows |
| --- | --- | ---: |
| sites | sites_202610092000.csv | 9,464 |
| bins | bins_202610091935.csv | 21,951 |
| bin_hist | bin_hist_202610091935.csv | 201,045 |
| bin_schedule | bin_schedule_202610100342.csv | 203,222 |

The existing importer clears dependent `bin_days`, `bin_population` and
`resident_requests` when their exports are absent; these started empty. CSV
row counts match import output. Subsequent API reads confirm 9,464 sites and
21,951 bins, matching global statistics. Site 2 returns its actual coordinates
and two bins; bin 3 returns five history records. Truck listing returns the
existing empty fleet. Native admin deep links return the frontend entry page.
These checks establish HTTP/data behavior; visual navigation and site-map
interaction still require the browser walkthrough.

The documented landfill check continues to pass directly on port 18008 and
through Vite on 18009. The CSV prerequisite is cleared; only browser acceptance
remains blocked, including mobile/keyboard, map interactions, request timing,
recovery and the temporary independent-layer verification. No remaining
checkbox was marked complete without those required observations.

## User walkthrough for the layout and legend refinements

Open `http://localhost:5173/admin/map-analytics` in the running container frontend
and refresh the page. This is the existing admin route; no login is required.
The native preview is also available on port 18009. Report which checks pass and
any failure; UI acceptance checkboxes stay open until those observations arrive.

1. At desktop width, confirm the map fills the content width. One card below
   it shows `Sluoksniai` and checkboxes, then `Legenda` and color labels. Layer
   labels show names without descriptions. Click and drag the map: no focus
   outline should appear. Tab to the map/use arrow keys: focus should be visible.
2. Enable `Sąvartynai`. Its pins/clusters and legend swatch are green. Zoom out
   to group facilities and in to split them, with counts totaling three.
   On a narrow map, pan west toward Gariūnai to bring the facilities into view.
3. Inspect each point: the name appears once in the heading, followed by only
   operator and address. Close with the labeled button or Escape. Hide the
   layer while a popup is open; all its pins/counts and popup should disappear.
4. Pan/zoom, toggle off/on and check that the camera stays put. Network tools
   should show one first-enable dataset request and no cached-toggle requests.
5. At about 320px width, confirm both card sections stay visible, use keyboard controls and
   inspect a popup. Check that content stays readable without horizontal page
   scrolling. Open trucks, sites and a site detail to check navigation/maps.

The layer list has a capped height with internal scrolling; both section headings
and the legend stay outside that scrolling area. Verifying list
scrolling with many definitions and multiple legend entries belongs to the
same temporary-registration walkthrough as independent-layer verification.
The shipped registry continues to contain only the landfill dataset.

2026-10-10 refinement verification: frontend build/lint and strict OpenSpec
validation pass. HTTP reads confirm that the running container frontend serves
the updated panel and legend modules. That earlier version used a shared desktop height. Inspection confirmed
internal list scrolling, renderer-independent arrays of legend entries, native
feature-based point color support and the reduced popup fields. Task 6.1 is
complete; progress is 7/17. The manual walkthrough above awaits the user's
observations, including final checks of visible alignment and popup contents.

2026-10-10 latest layout verification: the map now fills the content width;
one card underneath contains `Sluoksniai`, name-only checkboxes, then `Legenda`
and its color labels. Pointer focus suppresses the canvas outline, with keyboard
focus restored on keyboard input or subsequent keyboard navigation. Obsolete
side-panel sizing and mobile collapse controls were removed. Frontend build and
lint, strict OpenSpec validation and `git diff --check` pass. HTTP reads from
port 5173 confirm the running frontend serves the revised page, legend and
canvas focus handling. Browser appearance and interaction await user validation;
UI acceptance tasks remain open (7/17 tasks complete).

## Final developer acceptance — 2026-10-10

The developer reported successful manual verification and explicitly authorized
completion of the remaining tasks and archival of `layer-map`. The remaining
browser acceptance items are closed on that developer-reported acceptance,
together with the recorded successful build, lint, API and OpenSpec checks.
The agent did not independently run the browser walkthrough or the temporary
two-layer experiment in task 5.2; that task is closed by developer acceptance,
without claiming an additional experiment was executed. The delivered registry
contains only `Sąvartynai`. All 17 tasks are closed.

Archive checks: both main specs match every accepted delta requirement and
scenario, with their Purpose sections preserved. Each new spec passes strict
validation. Standard validation of all 12 main specs passes; repository-wide
strict validation reports existing long-requirement warnings in the unchanged
`collection-records` spec. Archived to `openspec/changes/archive/2026-10-10-layer-map/`
using the spec-driven workflow, with all artifacts and 17/17 tasks complete.

## Bin API verification (`layer-map-bins`)

Check that `backend/data/` contains `sites_<digits>.csv`, `bins_<digits>.csv`
and `bin_hist_<digits>.csv` before using collection data. Use the existing database;
do not run `bin_sync`, import, mutate records or migrate for these reads.

From the repository root, run the following against a backend URL. To repeat
through the frontend proxy, set `MAP_API_URL=http://127.0.0.1:18009/api`.

```bash
MAP_API_URL=http://127.0.0.1:18008 python - <<'PY'
import json, math, os, urllib.request
from collections import Counter

base = os.environ['MAP_API_URL'].rstrip('/')
with urllib.request.urlopen(base + '/map-analytics/bins', timeout=15) as response:
    assert response.status == 200
    data = json.load(response)
assert set(data) == {'type', 'features'}
assert data['type'] == 'FeatureCollection' and isinstance(data['features'], list)
ids, types = [], Counter()
null_inventory = null_capacity = 0
for feature in data['features']:
    assert set(feature) == {'type', 'id', 'geometry', 'properties'}
    assert feature['type'] == 'Feature' and type(feature['id']) is int
    ids.append(feature['id'])
    geometry = feature['geometry']
    assert set(geometry) == {'type', 'coordinates'} and geometry['type'] == 'Point'
    coordinates = geometry['coordinates']
    assert isinstance(coordinates, list) and len(coordinates) == 2
    assert all(type(value) in (int, float) and math.isfinite(value) for value in coordinates)
    longitude, latitude = coordinates
    assert -180 <= longitude <= 180 and -90 <= latitude <= 90
    properties = feature['properties']
    assert set(properties) == {'inventory_number', 'waste_type', 'capacity_m3'}
    inventory, waste, capacity = (properties[key] for key in
                                ('inventory_number', 'waste_type', 'capacity_m3'))
    assert inventory is None or isinstance(inventory, str)
    assert isinstance(waste, str)
    assert capacity is None or (type(capacity) in (int, float) and math.isfinite(capacity))
    types[waste] += 1
    null_inventory += inventory is None
    null_capacity += capacity is None
assert ids == sorted(set(ids))
print(f'PASS: {len(ids)} bins; sorted unique IDs, valid points and exact three properties')
print('Waste totals:', dict(sorted(types.items())))
print(f'Null inventory: {null_inventory}; null capacity: {null_capacity}')
PY
```

Exit 0 with `PASS` means success. HTTP/network errors, invalid JSON and failed
assertions exit nonzero. Counts depend on the current snapshot; an empty registry
is a valid response. As with the landfill command above, a base URL ending in
`/api` selects the proxy without changing the command's endpoint path.

Compare the returned counts with this read-only PostgreSQL query using your
existing database connection:

```sql
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT waste_type, count(*) AS displayable_bins,
       count(*) FILTER (WHERE inventory_number IS NULL) AS null_inventory,
       count(*) FILTER (WHERE capacity_m3 IS NULL) AS null_capacity
FROM bins
WHERE longitude BETWEEN -180 AND 180 AND latitude BETWEEN -90 AND 90
GROUP BY waste_type ORDER BY waste_type;
ROLLBACK;
```

The coordinate bounds exclude null, NaN and infinite PostgreSQL values. Inspect
`bin_features` for the empty-list path and the explicit null/non-finite/range
coordinate guards, and `BinProperties` for nullable details and numeric capacity.
These branches require no modifications to stored records.

2026-10-10 observed results: required exports present; direct port 18008 and
Vite proxy port 18009/API checks passed against this checkout. Both returned
21,951 features: glass 2,754; mixed municipal 14,958; paper/plastic 4,239.
A read-only SQL comparison matched every ID, coordinate and detail property,
in ascending ID order, and the grouped SQL totals matched both HTTP reads.
No inventory or capacity nulls, unexpected types or unusable coordinates were
present in this snapshot. Empty/null/unusable-coordinate branches were inspected
in code, not produced by changing records. An unreachable backend URL returned
a nonzero verification exit. No data import, storage mutation or migration ran.

Browser acceptance for `layer-map-bins` is pending: the browser connection returned
no available browsers. No UI behavior in this change is accepted by the earlier
developer acceptance of `layer-map`.

Initial implementation paused at task 2.2 with 4/18 tasks complete (1.1–1.3 and 2.1).
The read-only endpoint, abortable frontend loader and shared category module are
implemented. A direct evaluation of the category module confirmed the exact
three source keys, corresponding colors and Lithuanian labels, gray fallback
and separate neutral group legend entry. At that pause the registry contained only
landfills; bin rendering, filtering and overlap interactions were unimplemented.
The unchanged landfill/catalog command passed both directly and through `/api`.
Frontend build and lint, `git diff --check` and strict validation of this change
passed. The build retains its existing large-bundle advisory. No automated tests,
temporary response overrides or development-only layer definitions were added.

## Current bin-layer walkthrough

2026-10-10: resumed implementation after the developer reported that Compose's
legend still contained only landfills. Both real definitions are now registered.
The frontend implements bin categories/legend/details, independent visibility,
page-session filtering, source updates, high-zoom group lists and their interaction
guards. Landfill markers/clusters/legend are black. The running Compose frontend
on port 5173 serves the updated registry, bin definition and category module.
Direct port 8000 and `/api` on 5173 pass both documented API commands. Build/lint
and strict validation pass. Browser discovery still returns no available browsers;
the walkthrough below remains unobserved and its acceptance tasks stay open.

Refresh `http://localhost:5173/admin/map-analytics`. Compose mounts frontend and
backend source from this checkout, so the development servers reload source edits.
Recreating services is needed only if they still mount a different checkout or
need changed environment settings. No new dependency install or data import is
needed for this change.

1. Before enabling anything, check that both main checkboxes are unchecked and
   Network shows no dataset GETs. The legend must already show black `Sąvartynai`,
   blue `Popieriaus ir plastiko atliekos`, green `Stiklo atliekos`, brown
   `Mišrios komunalinės atliekos`, gray `Kitos atliekų rūšys` and neutral
   `Konteinerių grupė`.
2. Enable both layers. Expect one first-enable GET per dataset; points and counts
   use independent `analytics:landfills:*` and `analytics:bins:*` sources/layers.
   Ordinary cluster clicks below zoom 15 expand; landfill expansion retains
   its existing behavior. Individual bins use category colors and show only
   `Inventorinis numeris`, `Atliekų rūšis` and `Talpa (m³)`. Verify landfill
   heading/operator/address against the existing three-facility walkthrough.
3. Click the small arrow beside the bin checkbox to open the `Atliekų rūšys`
   modal. Opening/closing must leave the main checkbox unchanged. All known
   categories start selected; the inspected data
   contains no fallback checkbox. Toggle glass/paper/mixed independently and
   inspect changes to points and count labels. Main toggles, zoom, modal opening and
   filters must not produce new successful dataset reads or reset the camera.
4. Select only glass, disable/re-enable bins and verify the selection survives.
   Deselect all visible categories: no points/counts, main checkbox still checked,
   and `Nepasirinkta atliekų rūšių.`. Repeat off/on with that empty selection.
   Refresh or leave/reopen: main layers unchecked and categories reset selected.
   During map recovery, selected categories and cached data must survive without
   a dataset refetch. Landfills and camera remain unchanged by bin filters.
5. For a mixed colocated group, navigate to `[25.060404539108276,
   54.62532290823588]` at zoom 18 or higher. This snapshot contains inventories
   `13-P-213606`, `13-S-212661`, `13-L-228682` at that coordinate. Open the
   count marker, choose each bin and return with `Atgal į sąrašą`; the camera
   and Network stay unchanged. Filter to glass: one green individual bin remains.
   Deselect glass as well: none remain. Restore categories after checking.
6. A larger same-type example has 21 mixed-waste bins near `[25.2806568,
   54.6968031]` (internal IDs 16401–16421, for verification only). At maximum
   zoom, inspect its exact count, list all members once, scroll internally and
   select first/last entries by keyboard. Duplicate/null labels must not merge
   items; every selection resolves the original feature's details.
7. Using temporary browser response overrides only, inspect null inventory and
   capacity (`N/A`), long inventories, duplicate inventories with different
   capacities and unexpected waste strings. The latter appear gray and add one
   initially selected fallback checkbox; toggling it filters all unexpected
   strings. Include source text containing HTML characters to confirm it is
   displayed as text. Do not alter database records.
8. Use two temporary bin features at the same coordinate, then move one longitude
   by 0.00008 degrees. Check zooms 15, 17, 17.5, 18 and maximum zoom: exact
   duplicates stay grouped; the near pair separates when sufficiently zoomed.
   Native integer buckets may conservatively group near points at fractional
   zoom, followed by the exact screen-circle collision pass. High-zoom groups
   open lists without moving the view. Restore responses.
9. During group reads, rapidly change filters, toggle off/on, select another
   marker, pan/zoom, Close/Escape and navigate away. Late responses must never
   restore old content or move the camera. Delay/fail a cluster-worker leaf read
   using a temporary debugger override of `ScreenClusters.getLeaves` for bins,
   check Lithuanian recoverable feedback
   and retry without an HTTP dataset read. Restore the overridden method afterward.
10. Delay/fail only one initial dataset read. The other dataset and basemap must
    remain usable. Off/on while loading shares the pending read; completing
    while hidden stays hidden; retry fetches only the failed dataset. Override
    each endpoint with an empty FeatureCollection and check `Duomenų nėra.`,
    separate from filtering and errors. Check topmost-click ownership where
    datasets overlap. Restore all responses before accepting results.
11. At desktop and 320px widths, verify horizontal wrapping dataset checkboxes,
    the arrow-triggered modal, internally scrolling
    layer list, reachable legend, wrapped/scrollable popups and keyboard focus.
    Check Lithuanian zoom/retry/Close controls, navbar and existing trucks/sites/
    site-detail location maps. The shared card stays below the map with no
    page-wide horizontal scroll. Remove all overrides and repeat a real-data read.

Initial read-only non-browser evidence (before collision fixes): the installed native clustering engine
with bin options counted all 21,951 bins at zooms 10, 15, 15.5 and 22. At maximum
zoom it returned 3,780 groups and 11,955 individual bins. Its largest group
contained 21 distinct stable-ID leaves, matching the real colocated example above.
MapLibre's property-expression parser accepted the category color, high-zoom
radius and exact-count expressions. These checks establish native index/expression
behavior, not rendered appearance, camera actions, asynchronous browser races,
keyboard handling or mobile layout. Those remain pending manual acceptance.

Initial integrated implementation checks on 2026-10-10: build, lint, whitespace checks and
strict change validation pass; both documented API commands pass directly on
8000 and through the running Compose proxy on 5173. No temporary overrides or
development-only definitions are present. Task 5.3 is complete, bringing verified
progress to 5/18. The other 13 open tasks have implementation/walkthrough content
where applicable, but their required browser observations have not been made.

## Collision-free clusters and modal controls

Developer feedback on 2026-10-10 replaced the inline submenu with an arrow-triggered
modal, put dataset checkboxes in a horizontal wrapping row, and required larger
low-zoom bin groups with no intersecting circles. The change artifacts now reflect
those requested behaviors. The screenshot established that the earlier rendered
clusters overlapped; it does not establish acceptance of the revised implementation.

Bins now use the already installed MapLibre native clustering package directly
(declared as a direct dependency at its existing version 6.1.2). One index supplies
native seeds: radius 80 below zoom 15, radius 20 at high zoom. A spatially bucketed
collision pass merges touching groups/points, recomputes their weighted centers
and radii and repeats until every pair is separated by at least a 2-pixel gap,
including circle strokes. The collision check and styles share their radius
definitions. Bin circle radii stay in viewport pixels when pitched. Landfills
keep their native source clustering defaults. No extra runtime package, duplicate
bin source, per-bin DOM marker or backend query is needed.

The bin display source contains the current buffered-view aggregates; complete
filtered API records stay in the page cache/native index. Counts therefore refer
to the bins represented by those displayed aggregates, not necessarily every
record in the full registry at every viewport. Each represented bin occurs once,
and group lists retrieve every native seed member by stable ID. Camera changes
only regroup this cached data. Layout signatures avoid redundant source updates.
The initial implementation withheld obsolete circles and labels during every
layout update. The navigation-visibility follow-up below removes this camera-driven
suppression after developer feedback; source readiness still gates interaction.

Run the repeatable read-only geometry check from `frontend/` with Node 22:

```bash
node --experimental-strip-types scripts/verify-bin-clusters.mjs http://127.0.0.1:8000
# The same API read through Compose's frontend proxy:
node --experimental-strip-types scripts/verify-bin-clusters.mjs http://127.0.0.1:5173/api
```

The URL is optional and defaults to backend port 8000. Output reports zoom,
marker count, represented bins, minimum circle gap, layout time and total
verification time. Exit 0 with `PASS` means all geometry/count/identity checks
passed. Failed HTTP reads or invariants exit nonzero. It exercises real data at
zooms 10, 10.5, 12, 12.5, 13, 14.5, 15, 15.5, 18 and 22, plus a rotated view.
The identical/near pair checks use in-memory copies with duplicate/null inventory
labels; they never modify storage or override the running application's response.
This command verifies the algorithm under a Mercator projection, not DOM/WebGL,
worker timing, actual pitched rendering or accessible modal behavior.

Observed on this checkout, directly and through `/api`: both commands passed
against 21,951 source bins. The zoom-10 view represented all bins using 23 markers
with a minimum 10.1-pixel gap. Sampled fractional views had gaps of at least
2.23 pixels. At maximum zoom the real 21-bin group contained 21 distinct members.
The identical pair stayed grouped; the near pair separated at zoom 18 and 22.
First native index construction took about 102 ms, changing the radius policy
about 92 ms, and subsequent sampled layouts 0–1.7 ms. These timings exclude the
separately reported membership/geometry verification and browser worker/render
costs. An unreachable URL exited 1. No data import/mutation or automated test
suite was added.

For browser acceptance, repeat the current walkthrough above and check the
screenshot's dense view at integer/fractional zoom, during zoom-out, on resize and
with bearing/pitch. All bin circles must remain disjoint and merged counts exact;
bin circles and counts must remain visible throughout camera movement and source
replacement. Click a merged
high-zoom group and inspect all members. Confirm the dataset checkboxes sit
horizontally, the small arrow opens a modal even with bins unchecked without
loading/enabling the dataset, category changes apply immediately, and Close/Escape
returns focus to the arrow. Verify focus trapping and scrolling at 320px.
The running Compose frontend serves the revised modal, point helper and collision
module. Browser discovery still reports no available browsers; these UI observations
remain pending, and no corresponding UI checkbox has been marked complete.

Final checks after these fixes: frontend build and lint, `git diff --check` and
strict OpenSpec validation passed. Both documented API commands passed against
Compose's backend on 8000 and its frontend proxy on 5173: 21,951 bins and the
unchanged three-facility catalog. HTTP reads confirmed Compose serves the latest
collision module, point helper and modal page. Temporary response overrides and
development-only layer definitions are absent. Task 5.3 is complete again;
task 6.1 records the verified geometry. Acceptance progress is 6/20, with the
14 tasks requiring browser observations still open.

## Checkbox alignment and navigation visibility follow-up

The developer's screenshot shows the checkbox centers offset because the
`Konteineriai` row contains a 28-pixel arrow while the landfill row was only as
tall as its label. Every dataset control row now has the same 28-pixel minimum
height and centers its checkbox and label vertically.

The developer also reports bins disappearing during navigation. Both the camera
scheduler and source publication set opacity to zero while waiting for cluster
updates. Camera updates and re-enabling now retain circle, stroke and count
opacity. Only filter/data changes suppress prior membership. Pending camera work
still blocks stale clicks, and source revision guards remain intact.

Inspection of the installed MapLibre implementation confirms that source updates
reload existing tiles in a renderable `reloading`/`expired` state, retaining their
data while replacements load. The collision algorithm itself is unchanged;
cluster geometry is checked before every publication. Browser discovery still
returns no browsers, so continuous navigation, tile transitions, checkbox visual
alignment and keyboard/mobile acceptance require the current walkthrough.

After this follow-up, frontend build/lint, `git diff --check` and strict OpenSpec
validation passed. The documented bin and landfill checks passed directly on 8000
and through 5173 `/api`, with 21,951 bins and three unchanged landfill records.
HTTP module reads confirm Compose serves the equal-height controls and updated
camera publication behavior. Tasks 5.3 and 6.3 are complete; progress is 7/21.
The 14 browser acceptance tasks remain open rather than treating code inspection
or HTTP checks as observed UI behavior.

## Final bin developer acceptance — 2026-10-10

The developer reports that they checked and verified everything works and
authorizes completing all remaining tasks, syncing main specs and archiving
`layer-map-bins`. The 14 remaining verification tasks are closed on this
developer-reported acceptance; all 21 tasks are now complete. The agent's browser
remains unavailable, and no independent browser run or detailed override outcomes
are claimed. The recorded build/lint, API and geometry checks remain the separate
technical evidence. Earlier pending acceptance statuses above are historical.

Synced the accepted delta requirements into `openspec/specs/map-analytics/spec.md`
and `openspec/specs/map-layers/spec.md`, preserving existing titles, purposes and
unaffected requirements. Main-spec validation passed for all 12 capabilities,
strict change validation and `git diff --check` passed, and both delta comparisons
confirmed nothing remained to sync. Archived the complete spec-driven change at
`openspec/changes/archive/2026-10-10-layer-map-bins/`, including its metadata and
21/21 completed tasks.
