# Monthly container adequacy verification

Branch: `high-risk-zones`. Commands run from `backend/` unless stated otherwise.
Alembic migrations through 0017 were applied to an isolated local PostgreSQL. No source regeneration or VASA synchronization was used.

## Repeatable commands

```bash
uv sync --extra analytics
uv run --extra analytics python -m app.interfaces.container_adequacy --help
uv run --extra analytics python -m app.interfaces.container_adequacy --all-complete --daily data/bin_days_20231010_20261009_enriched.csv
uv run --extra analytics python -m app.interfaces.container_adequacy --month 2026-09 --daily data/bin_days_20231010_20261009_enriched.csv
uv run --extra analytics python -m app.interfaces.container_adequacy.verify --data-dir data --sensitivity --report ../openspec/changes/archive/2026-10-11-monthly-container-adequacy/numerical-verification.json
uv run alembic upgrade head
uv run python -m app.interfaces.container_adequacy_import --all
python ../openspec/changes/archive/2026-10-11-monthly-container-adequacy/verify_api.py
```

The API verifier also needs `httpx` in its verification environment. It uses an
isolated uniquely named database schema and the actual router/CollectionSession; it drops only that schema after verification. Set DATABASE_URL and backend settings before running it.
It is a repeatable audit command, not an added automated test suite.

Generation used Python 3.12.3, SciPy 1.15.3, NumPy 1.26.4 in an isolated native
environment. The documented `uv sync` installed the lockfile (SciPy 1.18.1);
the exact documented September command also converged and reused identical saved bytes.

From `frontend/`, `node node_modules/typescript/bin/tsc -b`,
`node node_modules/vite/bin/vite.js build` and
`node node_modules/eslint/bin/eslint.js src/pages/map-analytics src/components/maps` passed.
Vite reports a large application chunk; no build errors occurred.

## Numerical and source evidence

- All 21,951 existing `bin_population.csv` resident factors matched within `1e-7`.
- Fixtures exercise the actual allocation: 600 residents / 3 m³ = 200 residents/m³;
  shared 100/200-resident areas receive 1/2 m³ of the same 3 m³ point and share pressure 100.
- Resident totals: 544,476 for each separate waste type. Attributed capacity sums
  are 6,097.95 / 8,939.39 / 4,359.81 m³ for mixed / paper-plastic / glass,
  exactly conserving capacity at positive-demand points. Do not add residents across types.
- Snapshot pressure references: 225 / 120 / 242.2 residents/m³, unchanged across months.
- 11,814 residential eligible bins; 10,137 registry bins outside that analysis scope.
  The daily cohort has 21,695 bins; 256 registry bins are absent from the retained calendar.
- Calendar: 2,842,045 rows, 2026-06-01 through 2026-10-09. June–September are complete;
  October has nine days and is excluded from complete-month publication.
- NULL/empty labels, level 3 versus level 4, duplicate bin/day and invalid labels were audited.
  Fitted priors converged for every generated type/month. Sparse/no-assessment states,
  posterior domains, shared-point consistency, count domains and preservation on failed
  publication were audited. Temporary files do not enter discovery.
- Highest-pressure points and longest distances are recorded in
  [core-verification.json](core-verification.json). Large outliers remain visible;
  defaults were not retuned to suppress them.

[delivery-verification.json](delivery-verification.json) records exact absolute
output paths, all five immutable input hashes, result hashes, method/policy/priors,
calendar coverage, point summaries and resident totals by type/category.
Source hashes matched the artifacts after generation and UI use.

## Generated artifacts and timing

Outputs are under `backend/data/analyses/container-adequacy/`, ignored by Git.
Each file has 42,237 area/type features (14,079 source areas × 3 types).
Counts below are **area/type features**, not distinct collection points or people.

| Month | File | Priority | Potential | Fill only | Ordinary | Insufficient | Unavailable |
|---|---|---:|---:|---:|---:|---:|---:|
| June | `adequacy_2026-06.geojson` | 1609 | 2927 | 359 | 11272 | 25770 | 300 |
| July | `adequacy_2026-07.geojson` | 1478 | 2949 | 452 | 11359 | 25699 | 300 |
| August | `adequacy_2026-08.geojson` | 1795 | 2741 | 504 | 11216 | 25681 | 300 |
| September | `adequacy_2026-09.geojson` | 1326 | 3013 | 417 | 11248 | 25933 | 300 |

First batch: 47.84 s read/coverage/snapshot; 20.60 / 14.05 / 15.48 / 17.17 s
per month for fitting, validation and publication. Each artifact is about 45.5 MB.
Repeated September generation reused SHA-256
`261b4090829c5e3e5d4a7d29ffa83f913341e7164637dd4a417964ba1790e832`.
On the locked environment, read time was 66.45 s and fit/reuse 42.78 s under concurrent UI verification.

The actual app runs at `127.0.0.1:8018`, connected to isolated PostgreSQL on
loopback port 5548; Vite at `127.0.0.1:5188` proxies to it. Migration 0017 created
`container_adequacy_analyses`, and the real `--all` CLI imported June–September.
`alembic check` reports no new upgrade operations, confirming ORM/migration alignment.
The local PostgreSQL runtime is confined to ignored `backend/data/adequacy-pg-*`
folders, obtained from the registry package documented by
[embedded-postgres](https://github.com/leinelissen/embedded-postgres).
It is a verification runtime, not an application dependency or a required deployment service.

Catalog and all four GeoJSON reads return HTTP 200 from the real running app.
Measured sizes, ETags and database-backed load times: [http-delivery.json](http-delivery.json).
Whole-month payloads remain about 45.5 MB; session caching avoids repeated month reads.

## Sensitivity

[numerical-verification.json](numerical-verification.json) records every month,
changed resident totals separately per type, changed point/type count and full
category counts. The baseline is q80, 300 m, N≥5, dates≥3, bins≥50%, probability≥90%.
Loose evidence is N≥3, dates≥2, bins≥25%, probability≥80%; strict evidence is
N≥10, dates≥5, bins≥75%, probability≥95%. All other parameters remain fixed.

| September variant | Changed point/types | Priority area/type features |
|---|---:|---:|
| Baseline | 0 | 1326 |
| q75 | 185 | 1449 |
| q90 | 307 | 897 |
| Access 200 m | 711 | 1399 |
| Access 500 m | 296 | 1261 |
| Loose evidence | 1235 | 3580 |
| Strict evidence | 989 | 417 |

Evidence sufficiency materially changes classification, especially for glass.
Uncertainty/coverage remain available in each artifact; sparse evidence is visible as its own category. None of these scenario
results establishes real-world causality or forecast accuracy.

## Database/API and manual UI evidence

[api-verification.json](api-verification.json) records a real PostgreSQL JSONB
round trip of all 42,237 features and complete metadata through the actual router.
The audit ran in 72.15 s and verified:

- Empty table succeeds; unknown and filesystem-style IDs return 404.
- Identical import preserves ID, revision and PostgreSQL row version (`xmin`), without an update.
- Failure in the second write rolls back the first replacement in the same batch.
- Malformed input is rejected before import and preserves stored rows.
- Import/replacement of September preserves August; catalog order is descending.
- Replacement changes catalog revision and HTTP ETag, with metadata/properties intact.
- Missing table produces HTTP 500 via the existing `CollectionSession` error handling.
  Its two expected error messages are part of the negative checks.
- The router/service use only SQLAlchemy reads, with no artifact/source file access or SciPy import.

The real app/database was inspected in the browser:

- Imported June–September appear with Lithuanian month names; September/mixed defaults.
- Analysis polygons load from PostgreSQL and use the same layer/legend controls.
- Short category names: `Didelė rizika`, `Galima stoka`, `Dažnas 4 lygis`,
  `Įprasta`, `Mažai vertinimų`, `Nėra įverčio`.
- Popup has seven short rows and one conclusion; methodology and synthetic-data
  notices are absent from popup, selection dialog and layer summary.
- High-risk example shows estimated area residents 44, point bins 2, point pressure
  711.1 versus 225, straight-line distance 171.8 m and level-4 assessments 5/5.
- At 320 px, document width and scroll width are 320. The inspected popup measures
  256 × 237.5 px and fits inside the map; all seven rows and conclusion are visible.
- Provenance, thresholds, posterior estimates and coverage remain intact in imported metadata/features.

Screenshots: [compact database-backed popup](map-database-compact.jpg),
[320px popup](map-database-320.jpg).

The initial UI/CLI/catalog expose completed months only. The shared-today contract
remains deferred in the capability spec/design/tasks and includes importing generated
partial-period GeoJSON before catalog/map refresh.

[final-audit.json](final-audit.json) records unchanged five source hashes and four
completed-file revisions. Import writes only selected analysis rows; generation and
map reads preserve the portable artifacts and original source data.
