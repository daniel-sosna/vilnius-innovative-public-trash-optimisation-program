# Container adequacy analysis

Run from `backend/`. Generation is offline; import and map serving use PostgreSQL.
Install Python 3.12 and the backend with optional analytics dependencies:

```bash
uv sync --extra analytics
uv run --extra analytics python -m app.interfaces.container_adequacy --help
```

For an existing native backend environment: `python -m pip install "scipy>=1.14,<2"`.
The API runtime needs only the normal backend dependencies; SciPy is imported by generation only.

## Inputs and assumptions

`VIPTOP_DATA_DIR` in the environment or root `.env` selects the data directory;
the default is `backend/data/`. Relative paths resolve from the repository root.
Required exports: `sites_<digits>.csv`, `bins_<digits>.csv`, `bin_hist_<digits>.csv`,
and `population_density_1ha.geojson`. Numeric export suffixes select the latest file.
Supply the enriched bin-day CSV explicitly with `--daily`; see [fill/QR generation](fill-qr.md).
Add missing exports from a teammate. Do not use `bin_sync` for development data.

Population and registry represent static snapshots. Declared residence estimates
do not measure live presence. Suppressed density assumes 5 residents/ha.
Container capacity is assumed to be m³; confirm the source units before physical planning.
Centroid distances are straight-line estimates and omit barriers or access restrictions.
Attributed capacity is shared through nearest residential collection points, not
containers physically located inside a polygon. Synthetic fill depends on resident
pressure and collection timing; association is not independent evidence of real shortages.

Method and behavior: [container adequacy spec](../../openspec/changes/risk-agent/specs/container-adequacy-analysis/spec.md),
[map API/UI spec](../../openspec/specs/map-analytics/spec.md).

## Generate and transfer

```bash
uv run --extra analytics python -m app.interfaces.container_adequacy --september-cutoffs --daily data/bin_days_20231010_20261009_enriched.csv
uv run --extra analytics python -m app.interfaces.container_adequacy --all-complete --daily data/bin_days_20231010_20261009_enriched.csv
uv run --extra analytics python -m app.interfaces.container_adequacy --month 2026-09 --daily data/bin_days_20231010_20261009_enriched.csv
```

`--data-dir`, `--bins` and `--population` override locations. Policy options are
listed by `--help`; defaults are recorded in each output. Generation reads the
source CSV once, fits each requested period and prints coverage, hashes, paths,
category counts, total bytes and timings. September preparation fixes the source
cohort from September 1 calendar membership; registry bins outside that cohort
are recorded as exclusions. Static pressure/access references are shared across
the cutoffs; assessment statistics are fitted separately for each prefix. Budget about two minutes for this supplied 2.84M-row source;
actual timings are recorded in the change verification evidence.

Outputs under `<data_dir>/analyses/container-adequacy/`:

| Preparation mode | Filename | Schema/method version |
| --- | --- | --- |
| Completed month | `adequacy_YYYY-MM.geojson` | 1 |
| September cutoffs | `adequacy_2026-09-DD.geojson` (30 files) | 2 |
Copy these self-contained files to the target host and import them using the command
below. Original exports and analytics dependencies are not needed on the receiving
host. GeoJSON files are ignored by Git; transfer
them with other data artifacts.

Identical inputs reuse the saved bytes. Changing inputs, policy or method requires
the explicit `--regenerate` flag; replacement changes the content revision.
Publication writes a temporary file beside its destination and replaces each
period atomically. Batch failures leave already published valid files intact and return
a nonzero exit code. Generation never imports into the database or modifies sources.

## Import for the map

Set `DATABASE_URL` and the other backend settings in the root `.env`, as described in
[development](../development.md). Apply migrations and import the generated collections:

```bash
uv run alembic upgrade head
uv run python -m app.interfaces.container_adequacy_import --all
uv run python -m app.interfaces.container_adequacy_import --file data/analyses/container-adequacy/adequacy_2026-09.geojson
```

With Docker, migrations run on backend startup; import from the repository root:

```bash
docker compose exec backend uv run python -m app.interfaces.container_adequacy_import --all
```

`--all` uses the configured data directory. Repeat `--file` to select several files.
Import upserts the selected monthly or dated collections into `container_adequacy_analyses`
in one transaction. Reimport after explicit regeneration to publish its new revision.
Refresh the map's analysis list after import. Generated files alone do not publish
map data; the API reads PostgreSQL. Source GeoJSON can be moved after import.

Repeatable verification commands and recorded evidence are in
[the change](../../openspec/changes/risk-agent/verification.md).
