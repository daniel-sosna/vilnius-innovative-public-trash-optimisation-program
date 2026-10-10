# Population map verification

## Isolated runtime

Verified on 2026-10-10 from `/home/stitas/Projects/viptop-layer-map-pop`.
Compose project: `viptop-layer-map-pop`; resolved configuration:
`/tmp/viptop-layer-map-pop-n8kbqzyh/compose.json` (temporary, outside Git).
Both build contexts and `/app` binds point to this checkout. Named volumes
are prefixed `viptop-layer-map-pop_`; existing Compose projects were preserved.

- Frontend: http://localhost:5175/admin/map-analytics
- Backend: http://localhost:8002/docs
- Database: localhost:5434; container connection uses this project's `db:5432`.

The resolved configuration replaces published ports with 5175/8002/5434,
retains internal ports, and sets the backend connection to
`postgresql+psycopg://viptop:viptop@db:5432/viptop`. Repository Compose mappings
are unchanged. The temporary configuration contains resolved environment
values, is mode 0600, and should not be committed.

For a shell with current Docker group membership:

```bash
POP_CONFIG=/tmp/viptop-layer-map-pop-n8kbqzyh/compose.json
pop_compose() { docker compose -p viptop-layer-map-pop -f "$POP_CONFIG" "$@"; }
pop_compose up --build -d
pop_compose ps
curl --fail http://localhost:8002/docs >/dev/null
curl --fail http://localhost:5175/ >/dev/null
pop_compose exec -T backend uv run python -m app.interfaces.table_import
pop_compose exec -T backend uv run python -m app.interfaces.bin_population
```

If this shell predates addition to the Docker group, run the same commands
inside `sg docker`; a fresh login also picks up the membership. Configuration
can be regenerated with `docker compose config --format json` from this
checkout: set project name and volume names to `viptop-layer-map-pop`, replace
each service's published port, and preserve the resolved absolute build/bind
paths. Check availability of the chosen ports before starting a new stack.

## Data setup results

All required exports and `population_density_1ha.geojson` were present. Import
and population rebuild both exited 0, in that order. Imported all available
exports: 9,464 sites, 21,951 bins, 201,045 history rows and 203,222 schedule rows.
Population rebuild stored 14,079 polygons (7,508 suppressed; 100 missing density)
and 21,951 allocations. No bins lack an allocation or polygon. Resident estimates
total 544,476; allocation totals equal 544,476 separately for glass, mixed
municipal and paper/plastic waste. No `bin_days` rebuild or VASA synchronization
is required for this map.

Repeat the read-only allocation checks against the isolated database:

```bash
pop_compose exec -T db psql -U viptop -d viptop <<'SQL'
SELECT (SELECT count(*) FROM population_cells) AS polygons,
       (SELECT count(*) FROM bin_population) AS allocations;
SELECT count(*) AS missing FROM bins b
LEFT JOIN bin_population p ON p.bin_id = b.id WHERE p.bin_id IS NULL;
SELECT count(*) AS without_polygon FROM bin_population WHERE population_cell_id IS NULL;
SELECT b.waste_type, round(sum(p.resident_factor)::numeric, 6) AS allocated,
       (SELECT round(sum(residents)::numeric, 6) FROM population_cells) AS residents
FROM bins b JOIN bin_population p ON p.bin_id = b.id GROUP BY 1 ORDER BY 1;
SQL
```

Expected for this snapshot: `14079 / 21951`, zero missing, zero without polygon,
and equal per-type totals. These counts describe this snapshot, not API constants.

## Read-only API comparison

```bash
pop_compose exec -T backend uv run python -m app.interfaces.map_analytics.check \
  --url http://127.0.0.1:8000/map-analytics/population-cells \
  --url http://frontend:5173/api/map-analytics/population-cells --host localhost
```

Both URLs are configurable; `--url` may be repeated. The Host override lets
Vite accept the internal `frontend` service address through its development
host allowlist. For a native backend, run the module from `backend/` with
`DATABASE_URL` pointing at localhost:5434 and use the public URLs on 8002/5175
without `--host`. The command opens a repeatable-read, read-only snapshot and
compares every ID, ring, numeric/suppressed estimate and missing-density null
with independent SQL, reporting response bytes and elapsed time. Exit 0 means
all comparisons pass; HTTP, database or contract failures exit 1.

Endpoint edge checks performed against this isolated database: a temporary
empty schema served through the same router and collection dependency returned
HTTP 200 with an empty FeatureCollection. An exclusive transaction lock on the
real population table caused the running backend's read to return HTTP 500,
`Collection read failed`, after its lock timeout. The transaction was rolled
back and temporary schema dropped; the snapshot was preserved.

Measured responses: 5,773,480 bytes from both backend and proxy; 0.346/0.354 s
respectively on the first recorded comparison. Source states: 6,471 numeric,
7,508 suppressed and 100 missing. An intentionally wrong endpoint caused the
comparison command to exit 1, confirming failure is observable.

## Browser walkthrough

Open the frontend URL above in a fresh page session. Both checkboxes start
unchecked; the legend already contains the green landfill entry, five purple
population bands with `gyv./ha`, and the bordered transparent missing-data entry.
No analytics requests should occur until a checkbox is selected.

1. Check `Gyventojų tankumas`. Observe `Kraunami duomenys…` while reading, then
   translucent source polygons. Pan and zoom; basemap labels should stay legible.
2. Locate the real examples below. Longitude precedes latitude in the table.
   Click the polygon interior, away from markers; the camera must not move.
   Check the three labelled rows and the declared-residence/estimate explanation.
3. Close details using the labelled close button or Escape. With population
   details open, uncheck population: both polygons and its popup disappear.
   Re-enable it: no new population request should occur in this page session.
4. Enable landfills and repeat in both orders, using a fresh page for the reverse
   order. Pins and cluster counts remain green and above population. Cluster
   clicks expand, point clicks show facility details, and toggles preserve camera.
   Hide population while landfill details are open: those details must remain.
5. Trigger map recovery (for example by interrupting its style request, then
   restoring it and using map retry). Cached datasets and camera are restored
   without additional dataset reads. Leave and reopen the analytics page: the
   new session starts unchecked and requesting a dataset once attaches one
   source and its expected layers, with no duplicated interactions.
6. Repeat at 320 px viewport width. Labels and legend entries wrap inside the
   card, the map pans/zooms, and popup content scrolls with usable close controls.
   The document should have no horizontal overflow.

Verified real examples (zoom about 16–17 for cells):

| Meaning | Polygon ID | Interior longitude, latitude | Expected details |
| --- | --- | --- | --- |
| Numeric single cell | 5807 | 25.27617452, 54.71007982 | 15 gyv./ha; 1 ha; approximately 15 residents |
| Suppressed single cell | 5804 | 25.26996840, 54.71014393 | `<11`; 1 ha; approximately 5; applied assumption 5 gyv./ha |
| Merged numeric cell | 3380 | 25.24947492, 54.73342080 | 69 gyv./ha; 3 ha; approximately 207 |
| Missing-density remainder | 14079 | 25.03888150, 54.57240393 | No fill, outline or click target; API residents null, storage placeholder 0 |
| Populated island inside remainder's first hole | 87 | 25.36383378, 54.81028684 | `<11`; 3 ha; approximately 15; belongs to 87, not remainder |

The remainder is about 63,255 ha (632.55 km²), with 149 rings: one exterior and
148 holes. SQL geometry comparison and browser source inspection preserved all
of them. This snapshot has no known-density polygons with holes; a temporary
browser-only hole added to cell 5807 verified that its hole has no fill or click
target while its surrounding area remains interactive. Original data was restored.

All three real landfills lie inside missing-density territory in this snapshot.
To verify overlap priority, use a local browser response override containing a
known polygon beneath their recorded coordinates. For example, retain feature
5807's properties and replace only its geometry with a rectangle whose ring is
`[[25.1,54.63],[25.2,54.63],[25.2,54.7],[25.1,54.7],[25.1,54.63]]`.
Do this only in the browser, without changing stored data. Verify both enable
orders at zoom 16 at Gariūnų (25.1563,54.6567), and the three-facility cluster at
zoom 9. Point clicks must show only facility details; cluster clicks must expand
without a population popup. A polygon click at (25.145,54.67) must show population
details with no camera change. These checks passed in both orders.

The renderer's actual style expressions were evaluated with densities 10, 11,
49, 50, 99, 100, 199 and 200: expected five-band colours passed at every boundary.
Equal density on different areas/totals produced equal colours; suppression
used the lowest band and missing density failed both style filters. Browser
popup checks also covered assumptions 5 and 10 from stored totals/area, zero
area without division, and Lithuanian formatting `1 234,57` / `17 283,9`.

Lifecycle results: hover cursor `pointer`; hide cleared cursor, both style
layers and the owned popup; repeated toggles caused zero new reads. Recovery
restored the same camera with two analytics sources and five unique style layers.
Leaving/reopening produced one map canvas and three delegated click handlers
(population area, landfill point, landfill cluster), with one fresh request per
enabled dataset. No browser JavaScript errors were observed.

## Desktop and narrow-screen results

Verified at 1440×1000 and 320×900 in local Chromium using software WebGL.
The in-app browser backend was unavailable, so the walkthrough used a local
headless browser against this checkout's running frontend. Browser inspection
exposed only the map instance via a temporary response override; repository
runtime code contains no verification globals.

The full population source was ready about 1.72 s after the first lazy request.
Drag panning changed the center and remained usable with all 14,079 polygons;
a 12-step drag plus inertia took about 2.05 s in this software-rendered browser.
Zoom controls worked, basemap labels remained above polygons, and landfill
clusters stayed green with readable counts. These timings include rendering
and interaction overhead; software WebGL does not establish hardware frame rates.
The uncompressed full-grid response remains about 5.77 MB, paid once per page
session when enabled; no additional delivery infrastructure was needed here.

At 320 px, both document and body scroll widths were exactly 320 px. Legend
entries fit within 254 px and long labels wrapped. Popup rows and explanations
fit the narrow viewport; close-button hit testing and clicking passed, as did
Escape. Visual inspection identified the navigation controls covering a popup
close button in one narrow-screen position; popup stacking was adjusted so the
close control remains usable above them. Map navigation remains available after
closing the popup. Desktop and mobile screenshots were inspected locally.

## Loading, failure and empty-response checks

Use browser Network controls or local response overrides only for this endpoint;
reload between response cases so each begins with a fresh page-session cache.
Restore normal networking and remove overrides when finished.

- Hold/throttle the population read, enable it and verify `Kraunami duomenys…`.
  Disable it before completion. Releasing the read must leave no population
  source, visible features or popup. Re-enable: exactly the one original request
  is reused. Actual result: passed, camera retained (25.18,54.66), zoom 11,
  landfills still checked, no source/popup attached while disabled.
- Return HTTP 503 (or block only the population request). Verify
  `Nepavyko įkelti sluoksnio.` and population's `Bandyti dar kartą` control.
  Restore the response and retry: only population loads again. Actual result:
  no source/popup after failure, two population reads total (failure + retry),
  no extra landfill request, camera and landfill visibility preserved. Hiding
  and re-enabling the failed layer retained its error until explicit retry.
- Override the response with `{"type":"FeatureCollection","features":[]}`.
  Verify `Duomenų nėra.` rather than loading/error feedback. Actual result:
  zero source features, no rendered population fills/outlines or popup; camera
  retained (25.2797,54.6872), zoom 11, and landfills remained checked.
- As an additional uncertainty check, override with only real missing-density
  feature 14079. Actual result: one cached source feature, no rendered features
  or popup, and no empty-dataset message (the source is nonempty).

All cases passed against this frontend using browser-local response controls.
Normal responses were restored afterward; no database values or application
network configuration were changed by these checks.

## Final checks

```bash
pop_compose exec -T frontend npm run build
pop_compose exec -T frontend npm run lint
pop_compose exec -T backend uv run python -m app.interfaces.map_analytics.check \
  --url http://127.0.0.1:8000/map-analytics/population-cells \
  --url http://frontend:5173/api/map-analytics/population-cells --host localhost
openspec validate layer-map-pop --strict
git diff --check
```

All commands exited 0. Build included a non-fatal bundle-size warning for the
1.55 MB main JavaScript bundle (about 439 KB gzip) and 508 KB map worker. Lint
reported no errors. The final API comparison passed every polygon through
both endpoints: 5,773,480 bytes each, about 0.729/0.742 s respectively while
other checks ran concurrently. OpenSpec strict validation and whitespace
checks passed. The implementation diff was reviewed, including new renderer,
manual verification command and guide.

No migration, dependency manifest/lockfile, default Compose configuration,
CSV importer or population allocation implementation changed. The isolated
Compose stack remains running for review at the URLs above. Review and archive
the OpenSpec change separately after acceptance; this implementation does not
integrate the other worktree's bin map layer.

## Integration with origin/main (2026-10-10)

Merged main at `260c7a1` into the population branch. The earlier results above
describe the original population implementation; this integration adds main's
bin renderer, filters, popup lifecycle and black landfill appearance. Shared
schemas/services/router and registry retain all three datasets. The analytics
page uses main's horizontal, wrapping checkbox layout unchanged, with aligned
labels and the waste-type arrow. The population delta's selection requirement
also retains the row layout and bin availability for later spec synchronization.

After `npm ci` in the isolated frontend container, build and lint passed.
Population API/storage comparison passed directly and through the proxy, and
`node scripts/verify-bin-clusters.mjs http://backend:8000` passed with all 21,951
source bins, disjoint circles and exact membership. OpenSpec strict validation
and staged whitespace checks passed.

Local Chromium checks passed: three checkbox labels aligned at the same desktop
row position; no unchecked dataset requests; 320 px document width without
horizontal overflow; wrapping controls and a usable waste-type modal. Both
enable orders retained bin priority over population. A real five-bin group over
known-density polygons opened exactly five entries and allowed individual
details. Hiding population preserved those bin details. Filtering to mixed
municipal waste preserved camera/population and triggered no additional reads;
an individual filtered point opened inventory `13-L-422778`. A 342-bin ordinary
cluster expanded without a population popup. No browser JavaScript errors were
observed. Desktop and mobile screenshots were inspected locally.
