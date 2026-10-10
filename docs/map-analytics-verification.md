# Map analytics verification

Final status (2026-10-10): manual verification accepted by the developer; all
17 tasks closed with their authorization. Earlier pending statuses below are
historical. See the final acceptance record at the end of this document.

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
   the screen belongs to the shared admin layout and only `Sąvartynai` is offered.
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
compact popup. The `Legenda` section in the card under the map displays a green
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
color expression. For a future categorized dataset, supply one labeled legend
entry per category and a uniform `appearance.clusterColor` for grouped points
(with its own legend entry if it differs). This adds no bin/waste dataset now.

A future non-point definition implements `MapLayerDefinition` directly: set its
render `kind` and geometry-independent legend entries, load a GeoJSON
FeatureCollection of its geometry, and implement
`attach(context, data)` returning `setVisible(boolean)` and `dispose()`. Attach
runs after style readiness; the renderer owns sources, style layers and events,
changes visibility without moving the camera, and removes everything on dispose.
`context.showDetails(id, coordinates, content)` and `closeDetails(id)` provide
shared popup ownership if needed. This boundary never calls a polygon a marker
or applies point clustering to it. Recovery attaches a new renderer against
retained cache; disposal must tolerate in-flight interaction completion.
No non-point renderer is delivered in this change.

## Temporary simultaneous-point verification

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
