# District boundary verification

Use a disposable database and a copy of the input folder. Never temporarily
rename or corrupt the shared source. No VASA synchronization or automated test
suite is needed. Check the selected directory first for `sites_<digits>.csv`,
`bins_<digits>.csv`, `bin_hist_<digits>.csv` and
`vilnius_seniuniju_ribos.geojson`; the population overlay also requires its
existing imported `population_cells` snapshot.

## Isolated stack and import

From the repository root, copy the data to a new folder and use free ports:

```bash
mkdir /tmp/viptop-dist-data
cp backend/data/*.csv backend/data/*.geojson /tmp/viptop-dist-data/
export VIPTOP_DATA_DIR=/tmp/viptop-dist-data
export FRONTEND_PORT=5176 BACKEND_PORT=8003 DB_PORT=5435
docker compose -p viptop-dist-verify up -d --build
docker compose -p viptop-dist-verify exec -T backend uv run python -m app.interfaces.table_import
docker compose -p viptop-dist-verify exec -T backend uv run python -m app.interfaces.bin_population
docker compose -p viptop-dist-verify exec -T db psql -U viptop -d viptop -c \
  'SELECT count(*) FROM district_boundaries;'
```

Expected: normal import exits 0 and reports the district source plus 21 districts.
All CSV counts must match the exports. Source geometry has 21 rings and 8,916
positions. Standalone native/container commands in README must also return 0;
two successive imports retain 21 names/geometries without changing collection
or population records. Generated district IDs may change.

## Import failures and preservation

Create separate case folders under the copied data directory so the backend
can see them as `/app/data/<case>`. Invoke
`python -m app.interfaces.table_import --dir /app/data/<case>` inside the backend
container, or use the host folder with the native CLI. The explicit directory
must win over `VIPTOP_DATA_DIR`; no input may be fetched from another folder.
Compare ordered rows before and after failures, including geometry and IDs,
as well as counts. These cases do not change stored snapshots:

| Case | Inputs | Expected exit and result |
| --- | --- | --- |
| Combined | Valid CSVs and district source | 0; both datasets committed |
| Invalid district | Valid CSVs; source is `{}` | 1; all previous rows preserved |
| CSV failure | Valid district; CSV has an unknown column or invalid final row | 1; all previous rows preserved |
| Unreadable source | Source filename is a directory or inaccessible file | 1; preserved; no successful empty import |
| Competing input | Source and `district_boundaries_1.csv` | 1; identifies both paths; preserved |
| Boundary only | Valid source, no CSVs | 0; only districts replaced |
| Missing source | CSVs, neither district input | 0; warning; districts preserved |
| Nothing | Neither input | 1; nothing changed |
| District CSV only | Export with all columns and valid IDs | 0; normal CSV replacement/sequence handling |

For standalone import, `--file /missing.geojson`, malformed JSON, an empty
FeatureCollection, duplicate name/OBJECTID, boolean OBJECTID, unsupported CRS,
projected/non-finite coordinates, open rings and zero-area rings must exit 1.
An invalid final feature must not remove earlier stored districts. Verify a
valid Polygon with a hole preserves that hole. Full topology repair is outside
the contract.

## Recorded import results

On 2026-10-10, the isolated `viptop-dist-verify` stack used ports 8003/5176/5435
and an independent input copy. Migration 0014 created an empty table;
downgrade to 0013 and re-upgrade preserved every other table. Native and
container standalone import succeeded with 21 districts. Invalid/missing
standalone sources exited 1 and preserved the exact catalog.

Combined, boundary-only, CSV-only and missing-source cases exited 0. Invalid
GeoJSON, unknown-column CSV, unreadable input (a directory at the source path),
competing source/CSV and empty-input cases exited 1. Ordered row hashes and
counts matched before/after every failure. Explicit `--dir` succeeded with
`VIPTOP_DATA_DIR` deliberately pointing at a missing directory. An invalid older
truck export was ignored in favor of the newer valid export.

Counts: 9,464 sites, 21,951 bins, 201,045 history rows, 203,222 schedules,
14,079 population polygons, 21 districts. The combined-input check also used
one disposable truck row. Population generation reported 7,508 suppressed and
100 missing-density polygons; its estimate assumptions remain unchanged.

## Read-only endpoint checks

Use the native/container checker commands in README, with explicit backend and
proxy URLs pointing at the same disposable database. Expected: 21 features,
21 rings and 8,916 positions; all ordered IDs, names and geometry match SQL.
The only property is `district_name`. Also check a valid interior ring by storing
an explicitly imported Polygon containing a hole in an isolated case and
comparing the response; never simplify coordinates or substitute a bounding box.

Temporarily rename the copied source and request both endpoints; responses must
remain identical. Create a different/invalid source without importing and
repeat; the stored response must still be identical. Restore the copy afterwards.
In the disposable database, save and temporarily remove catalog rows: both
endpoints must return HTTP 200 with `features: []`, and the checker must accept
the empty SQL snapshot. Restore rows, then temporarily rename the district table:
both endpoints must return HTTP 500 `{"detail":"Collection read failed"}`.
Restore the table in a `finally` block. A checker invocation against the landfill
endpoint must exit 1 with a credential-free failure message.

Recorded on 2026-10-10: direct and proxy payloads each contained 348,564 bytes,
matching all 21 districts/21 rings/8,916 positions (roughly 0.03 seconds each).
Missing source and changed-without-import reads retained exact responses; empty
catalog returned 200; table-unavailable query returned the existing 500 contract.
The checker exited 0 for populated and empty snapshots and 1 for a mismatched
endpoint. The copied source and table were restored after each check.

## Map verification matrix

Open `/admin/map-analytics` in a fresh session. Use the regular configured
OpenFreeMap style and actual stored datasets. All four checkboxes must start
unchecked with zero map-dataset requests. Keep the existing legend text/count
for comparison; districts add no entries. Inspect the map's source and style
layers with browser developer tools where a visual result alone is ambiguous.

| Check | Procedure | Expected result |
| --- | --- | --- |
| Lazy/cache | Enable districts, hide, re-enable | One request; both district style layers hide/show; same map and camera |
| Pending read | Delay district HTTP response; disable before completing it | Cache may fill but districts remain hidden until re-enabled |
| Retry/empty | Return one HTTP 500, retry; separately return empty collection | Lithuanian failure/retry; independent recovery; empty feedback without retry |
| Attach order | Districts → population; fresh session population → districts; delay either response | District fill/outline below population fill/outline, then point styles; relative point order preserved |
| All datasets | Enable landfills, bins, population and districts | Distinct boundaries, purple density, points/counts and basemap remain readable |
| No district names | City zoom 10/10.5; neighborhood zoom 12/12.5 and closer; toggle overlay | Colored fills/outlines remain visible without district name labels at every zoom |
| Palette | Compare all API names with `districtColors`; reorder features/toggle | 21 unique vibrant name/color pairs; visibly distinct translucent areas and boundaries; colors independent of generated IDs/order |
| District interaction | Click fill/line alone; inspect delegated handlers | No district popup, cursor interaction, selection or camera movement; zero district handlers |
| Population | Click numeric and suppressed cells; click over district areas; click missing-density cell | Existing details/assumption preserved; district rendering does not block clicks; missing density has no popup |
| Popup ownership | Open population/bin details, hide districts; then hide owning layer | District toggle retains unrelated popup; owner hide closes it |
| Point priority | Click bin/landfill marker or count over density/districts | Only point interaction; ordinary clusters expand; high-zoom bin groups open their list |
| Bin grouping | Zoom 15+, overlap/identical-coordinate group; select bin and return | Exact count, existing detail fields and back-to-list behavior; no population popup |
| Filters | Disable a bin category, toggle districts, reopen category dialog | Category and counts persist; no bin dataset reload or camera change |
| Narrow screen | Repeat with viewport width 320 pixels, city and neighborhood zoom | No horizontal overflow; reachable controls; existing legends wrap; district names remain absent |
| Source independence | Rename copied source; fresh API request and fresh page session | Stored districts still render; restore copied source afterwards |

Use browser network interception only for delayed/error/empty response checks;
use real responses for normal rendering and interaction. Districts attach fill
and outline styles only. No district symbol/text style is attached. The shared
Polygon helper retains optional labels for other definitions.

## Original verification before district label removal

The following recorded results describe the original implementation, including
its labels; the current layer omits names following the user's revision.

Recorded map checks on 2026-10-10 used local Chromium with the in-app browser
unavailable. District rendering had no delegated click/hover handlers. All 21
source names matched distinct palette entries. Vilkpėdė's native zoom-10 anchor
was `[25.24130344390869, 54.66762675368648]`, inside the stored Polygon. City
zoom 10 showed 16 district names before enabling other datasets; count markers
suppressed crowded district names as intended. Zooms 10.5, 12 and 12.5 and a
320-pixel viewport retained readable boundaries and labels where space allowed.
The narrow document width was exactly 320 pixels with no horizontal overflow.

Both attachment orders produced district fill/outline/labels, population
fill/outline, landfill clusters/counts/points, then bin clusters/counts/points.
Point order was preserved. Numeric density 17 and suppressed `<11` details
retained formatting and the 5 gyv./ha assumption; a missing-density cell opened
no popup. Population clicks at district text still opened population details.
Hiding districts hid all three styles while keeping population details open;
hiding population closed its own popup. Toggles preserved the map instance,
camera and cached district response. A delayed disabled read stayed hidden
and re-enable used its one cached request. Injected failure/retry and empty
response feedback passed while another layer remained usable.

## Original complete-system results before district label removal

The regular container import committed all four supplied CSV tables together
with 21 districts. The direct and proxied SQL comparison passed afterwards.
With the copied source renamed out of the configured directory, a fresh API
request and fresh map session enabled all four datasets successfully. Fitting
the map to the stored bounds rendered 21 unique district IDs. At city zoom 10
in a 320-pixel viewport, eight district names were visible; the document had
no horizontal overflow. The missing-source regular CSV import exited 0 with
the expected warning, and its fresh district response exactly matched the
already loaded response, including IDs and coordinates. The copied source
was restored using a shell cleanup trap.

An isolated temporary `NOT VALID` check constraint rejected the final district
source ID 442 during insertion. Standalone and regular imports each exited 1;
the regular case failed after loading the selected CSVs and deleting the old
catalog. Ordered row hashes for sites, bins, history, schedules, population
and districts all matched before/after, proving transaction rollback even on
late district failure. The constraint was removed in a `finally` block. An
explicit temporary snapshot containing an interior Vilkpėdė ring was also
imported and returned exactly by both endpoints, then the supplied snapshot
was restored. These operations used only the isolated database/data copy.

Delaying district completion while all other datasets were visible still
placed its styles below population and points. Bin count 421 expanded from
zoom 10 to 11 without opening population details. At zoom 17, a screen-space
group containing four co-located bins plus nearby bins opened an exact
seven-item list; selecting a bin showed inventory, waste type and capacity,
and returning restored seven items. District toggles preserved the bin popup.
The landfill point opened its existing facility/operator/address details.
The disabled glass category and camera survived district toggles; existing
legend content remained unchanged.

Final checks: frontend `npm run build` and `npm run lint`, Python module/schema
loads, CLI help/native/container commands, `alembic check`, `git diff --check`
and strict OpenSpec validation passed. Alembic detected no new upgrade
operations. The build retains the pre-existing large-bundle advisory; native
uv commands reported that an inherited environment belonged to another
checkout and correctly used this checkout's `.venv`. No automated test suite
was added. Verification screenshots and temporary scenario scripts remain
outside the repository under `/tmp`; the focused read-only checker is the
maintained repeatable command.

## District label removal verification

On 2026-10-10, after removing district labels, frontend `npm run build` and
`npm run lint` passed. A fresh Chromium session on the isolated running stack
loaded all 21 districts with exactly two district styles: fill and outline.
No district symbol style was attached at zooms 10, 10.5, 12, 12.5 or 17.
Disabling and re-enabling the overlay hid and restored both styles without
changing the camera or adding labels. District colors and stored/API names
remain available for stable identity. Strict OpenSpec validation and
`git diff --check` passed; the build retains its existing bundle-size advisory.

## Vibrant district palette verification

On 2026-10-10, the user's contrast refinement replaced the muted palette with
21 distinct saturated colors, increased fill opacity from 0.18 to 0.32, and
strengthened outlines from 1.4 px at 0.85 opacity to 1.8 px at full opacity.
Fresh Chromium checks confirmed these paint values and all 21 palette entries
on the isolated running stack. Visual inspection with districts alone and all
four datasets enabled confirmed stronger area/boundary contrast, readable
basemap streets/text, purple population shading and point/count markers above
the district areas. District toggles retained the camera; no district symbol
layer appeared at zooms 10, 10.5, 12, 12.5 or 17. Frontend build/lint, strict
OpenSpec validation and whitespace checks passed. The existing bundle-size
advisory remains. Verification scripts and screenshots are outside the repo.
