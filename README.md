# VipTop Waste Collection Optimisation

VipTop MVP for exploring more efficient public waste-container collection in Vilnius. Administrators can manage the truck fleet through the Lithuanian UI and persistent API. The backend also stores collection records and imports address-grouped sites, physical bins and service history from VASA on explicit command invocation. Prediction, route generation, and driver interfaces are future changes.

## Technologies

- React, TypeScript, Vite, Tailwind CSS, and shadcn/ui
- Python 3.12, FastAPI, Uvicorn, SQLAlchemy, psycopg, Alembic, and pydantic-settings
- PostgreSQL
- Docker Compose

## Project structure

```text
.
├── frontend/                # React web application
├── backend/
│   ├── alembic/            # Reviewed database migrations
│   ├── alembic.ini
│   ├── start.sh            # Migrate before starting the server
│   └── app/
│       ├── core/           # Configuration and shared setup
│       ├── domain/         # Business concepts and rules
│       ├── repositories/   # Data-access abstractions
│       ├── services/       # Reusable application services
│       ├── use_cases/      # Application workflows
│       ├── interfaces/     # trucks/ HTTP API, bin_sync/, bin_schedule_sync/, table_import/ and bin_days/ CLIs
│       ├── infrastructure/ # Database engine and ORM persistence
│       ├── integrations/   # Third-party clients and source mapping
│       ├── ml/             # Future prediction logic
│       ├── optimization/   # Future route optimisation logic
│       └── main.py
├── scripts/                 # Future database and utility scripts
├── docs/                    # Repeatable manual verification
└── docker-compose.yml
```

## Run locally

Docker and Docker Compose are the only prerequisites. From the repository root, create `.env` if it does not already exist, then start the complete development environment:

```bash
test -f .env || cp .env.example .env
docker compose up --build -d
```

When switching from the earlier `bins-ui-update` schema, discard its disposable
database before starting this merged version:

```bash
docker compose down --volumes
docker compose up --build -d
```

This removes all existing database records and recreates dependency volumes;
CSV files under `backend/data/` remain on disk for your later import. The old
branch used `0005` for resident requests and `0006` for manual collection
management; main uses those revisions for truck volume and landfills. An old
branch database cannot be upgraded using those ambiguous version numbers.
Start with empty storage instead of stamping it to a newer revision. The merged
chain keeps main's revisions through `0012`, resident requests at `0010`, and
manual collection management at `0013`. Startup prepares the schema and seeds
the landfill catalog, without importing collection data.

To activate collection browsing after import, with the existing database already
running, rebuild the application images and refresh the frontend dependency
volume before recreating the application services:

```bash
docker compose build backend frontend
docker compose run --rm --no-deps frontend npm ci
docker compose up -d --no-deps backend frontend
```

The dependency refresh installs MapLibre into the existing `frontend_node_modules`
volume. These commands retain PostgreSQL and its imported records. The normal
backend entrypoint checks the existing Alembic revision; no new migrations were
added by collection browsing, and startup does not run the importer.

The services are available at:

- Frontend: <http://localhost:5173>
- Backend: <http://localhost:8000>
- FastAPI docs: <http://localhost:8000/docs>

`DATABASE_URL` and positive finite `BIN_SYNC_HTTP_TIMEOUT_SECONDS` are required.
VASA tile/detail/history URL templates default to the HTTPS endpoints in
`.env.example`; override them through dotenv or environment when needed. For an
existing `.env`, replace `BIN_SYNC_SOURCE_URL` with the three `VASA_*_URL_TEMPLATE`
settings from the example and retain your connection and timeout. Leftover
unrelated settings are ignored; the importer does not rewrite operator files.

The backend entrypoint runs `alembic upgrade head` before Uvicorn. **Revision
0004 deliberately drops old bins, routes, route stops and service events.**
Trucks survive revision 0004 unchanged. **Revision 0005 requires an empty legacy
truck table**, including retired rows, then replaces site-count capacity with
positive finite `max_volume_m3 NUMERIC` and required unrestricted
`waste_carrier TEXT`. If trucks unexpectedly exist, migration fails with their
IDs without converting counts, inventing carriers or deleting records. Its
downgrade to 0004 also requires an empty truck table. **Revision 0006 creates
and seeds `landfills` and adds nullable `trucks.landfill_id`**. It preserves
existing active/retired trucks as unassigned. Downgrade to 0005 refuses any
assigned truck, including retired rows, rather than dropping assignments.
**Revision 0007 makes all landfill fields except `id` and `name` nullable**.
It preserves catalog values and assignments; downgrade to 0006 refuses rows
with newly optional details still NULL instead of fabricating missing values.
Preserve a backup before
upgrading if old collection records are needed. Migration failure prevents startup. Startup, restart, reload,
migrations and idle runtime perform no VASA requests or cleanup.

After schema preparation, load the collection data (`sites`, `bins`, `bin_hist`)
from CSV exports as described in [Import table CSV exports](#import-table-csv-exports):

```bash
docker compose exec backend uv run python -m app.interfaces.table_import
```

**Do not use `bin_sync` for development.** Parsing the VASA API is very slow (a
full pass takes hours) and depends on the external source. It is only for
refreshing the shared data snapshot; see [Bin synchronization](#bin-synchronization).

To run the backend outside Docker, install [uv](https://docs.astral.sh/uv/), provide an accessible PostgreSQL database, and run from `backend/`:

```bash
export DATABASE_URL=postgresql+psycopg://viptop:viptop@localhost:5432/viptop
uv sync --locked
uv run alembic upgrade head
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

After the native server is running, open another terminal in `backend/` and import the CSV exports once using the same accessible connection:

```bash
export DATABASE_URL=postgresql+psycopg://viptop:viptop@localhost:5432/viptop
uv run python -m app.interfaces.table_import
```

These credentials are the local Compose defaults; use the connection details for your database. Native commands, including Alembic and the importer, load the repository-root `.env` using the configuration module's location, independent of the working directory. The shared file can include `POSTGRES_*` settings. Exported variables override dotenv values: the localhost connection above overrides the example's container-only `db` hostname. No exported synchronization variables are needed when the file contains them. Standalone images obtain all required settings from their environment and do not need a copied or mounted dotenv file.

## Resident emptying requests

Open `/resident-request/{bin_id}` using the bin's internal `Bin.id`, for example
`/resident-request/1`. This is a public Lithuanian page designed for phones,
independent of admin navigation. The supplied Vilnius logo is centered above
the title in every pre-success state and disappears with the form after success.
A fixed map beneath the title marks the bin’s
physical coordinates and prevents movement or zoom. The first field is `Adresas`
from the linked collection site, followed by inventory number and waste type;
unknown values display `N/A`. Map loading/failure does not block submission.
When history exists, a pale translucent light-blue information card is centred
in the space between the fields and button. It shows `Paskutinis aptarnavimas atliktas`
and only the latest bin history calendar date; no history means no card.
Stored Vilnius dates are displayed without timezone conversion.
Pressing `Siųsti` stores a request and replaces all page content with a centred
large green circle, white checkmark, `Jau vykstame pas Jus`, and the supplied
responsive GIF beneath the text. The action is disabled while pending and
removed after success. Failed submission
shows `Kažkas nepavyko. Bandykite dar kartą.` and allows retry. A missing bin shows
`Konteineris nerastas`; loading failures have a read-only retry.

| API | Behaviour |
| --- | --- |
| `GET /bins/{bin_id}` | Only `id`, `address`, `inventory_number`, `waste_type`, `latitude`, `longitude`, and nullable `latest_service` (`date`, `was_serviced`); missing bin 404, invalid ID 422 |
| `POST /bins/{bin_id}/resident-requests` | No body required; 201 `{"success":true}` after committing one request; missing bin 404, invalid ID 422 |

Frontend calls use the existing `/api` proxy. Positive IDs beyond BIGINT range
return 404. `resident_requests` contains only generated `id`, required `bin_id`,
and required `timestamp`. The database generates Europe/Vilnius local wall time
and stores it as `TIMESTAMP WITHOUT TIME ZONE`, independent of the UTC connection
setting. Parent-bin deletion cascades to resident requests, including importer
cleanup. Additive migration `0010` preserves existing collection records and
checkpoints. Startup applies migrations without running import.

Reports are raw resident signals; no verified fill, service event, prediction,
or route is generated. Separate submissions and a reload after success can
create additional requests. QR generation/scanning, accounts/authentication,
CAPTCHA, rate limiting, identity/IP/device capture, duplicate protection,
moderation, admin request management, ML/routing integration, and notifications
are outside this feature. See [resident request verification](docs/resident-request-verification.md)
for repeatable synthetic migration, API, SQL, failure, and mobile checks.

## Import table CSV exports

This is the required way to get collection data for development: load table
exports shared by a teammate instead of running a slow VASA synchronization.
Put the CSV files in `backend/data/` (contents git-ignored except `.gitkeep`, and
excluded from the Docker build) and run:

```bash
docker compose exec backend uv run python -m app.interfaces.table_import
# native, from backend/ with DATABASE_URL exported or set in the root .env
uv run python -m app.interfaces.table_import --dir /path/to/exports
```

- **File names:** `<table>_<digits>.csv`, e.g. `bins_202610091935.csv`. With several
  files for one table, the highest number wins. Other `.csv` files are ignored with a warning.
- **Export settings:** UTF-8, a header row with column names, unquoted `NULL` for null
  (as DBeaver writes it), quoted text. Export after running the same migrations.
- **Replacement:** only tables that have a file are emptied and reloaded (IDs are kept);
  other tables, such as `trucks`, are untouched. Importing `sites`, `bins` or `bin_hist`
  also clears the saved `bin_sync` runs and progress, so the next sync starts a fresh pass.
  A table referenced by a table without a file (e.g. only `sites`) is rejected.
  Importing `bins` also empties the derived `bin_population` and `bin_days` tables; refill
  them afterwards in this order: [Bin population](#bin-population-residents-per-bin), then
  [Bin-day calendar](#bin-day-calendar). The population polygons (`population_cells`) are kept.
  Importing `bins` without a `bin_schedule_<digits>.csv` also empties `bin_schedule` (the
  output says so), because planned dates belong to the replaced bins; fetch them again with
  the schedule command. With a `bin_schedule_<digits>.csv`, that table is loaded from the file.
  An import without `bins` (e.g. only `bin_hist`) leaves `bin_schedule` unchanged.
  Importing `bins` without a `resident_requests_<digits>.csv` also empties `resident_requests`
  (the output says so): the requests belong to the replaced bins and cannot be refetched.
- **Safety:** everything runs in one transaction; any failure leaves the database unchanged.
  **The current contents of the imported tables are discarded.**
- **Exit codes:** 0 on success, 1 if there is nothing to import, the directory is
  missing or the import fails.

**For AI agents:** before any task that needs collection data, check that
`backend/data/` contains `sites_<digits>.csv`, `bins_<digits>.csv` and
`bin_hist_<digits>.csv`. If any is missing, stop and ask the developer to add the
exports. Do not run `bin_sync` to obtain the data instead. Likewise, before building the
bin population, check that `backend/data/population_density_1ha.geojson` exists; if it is
missing, stop and ask the developer to add it.

See [table import verification](docs/table-import-verification.md) for repeatable checks.

## Bin population (residents per bin)

`bin_population` estimates how many residents each bin serves, from the Vilnius
population-density grid. Place `population_density_1ha.geojson` in `backend/data/`
(git-ignored like the CSV exports), import the collection data, then run:

```bash
docker compose exec backend uv run python -m app.interfaces.bin_population
# native, from backend/
uv run python -m app.interfaces.bin_population --file /path/to/population_density_1ha.geojson
```

Options: `--file` (default `backend/data/population_density_1ha.geojson`) and
`--suppressed-density` (default 5, between 0 and 10). It takes a few seconds, replaces
`population_cells` and `bin_population` in one transaction (a failure changes nothing) and
exits 0 on success, 1 on failure. The summary prints polygon and resident totals, how many
bins have a polygon, and per waste type the residential bins, collection points, allocated
and unallocated residents, distance percentiles and factor percentiles (p50, p90, p99, max).

- `population_cells`: one row per source polygon (`id` = `OBJECTID`), with its density per ha,
  area, `residents` (density × area, assumed density applied) and geometry.
- `bin_population`: per bin, `population_cell_id` (polygon containing the bin, or NULL) and
  `resident_factor`, the **estimated** residents the bin serves (not observed). It is copied
  into `bin_days`.

Refill order: import, then bin population, then bin days. The bin-day rebuild refuses to run
while an eligible bin has no allocation (for example after a sync adds bins).

**Assumptions:**
- Each polygon's residents use the nearest residential collection point of each waste type
  (bins of that type at identical coordinates), measured from the polygon centroid. The
  point's residents are split among its bins by capacity.
- Residential means object group `Daugiabučiai namai`, `Dvibučiai`,
  `Daugiabučių/garažų bendrijos`, `Sodų bendrijos` or `Sodų/garažų bendrijos`, with capacity
  above 0. All other bins get factor 0; the generator supplies their baseline.
- The source value is a density per ha; merged polygons are allocated whole from their
  centroid. `"<11"` counts as 5 per ha, null as 0.
- Declared residence matches actual residence.
- Isolated points can take very large catchments (max about 7,600 residents for mixed waste);
  p99 and max are printed so outliers are visible.

See [bin population verification](docs/bin-population-verification.md) for repeatable checks.

## Bin-day calendar

`bin_days` holds one row per bin per calendar day. It is the input for the future
synthetic fill-level generator. It is derived from `bins`, the stored planned dates in
`bin_schedule`, `bin_population`, the requested dates, the Lithuanian public holidays and the simulation
parameters. It does not read `bin_hist`, and it holds no observed outcomes or fill levels.
The generator reads `bin_hist` itself and, when one bin has several events on the same day,
uses the last one. The generator should reset fill on `collected` and `retry_collected`.

Build it after importing the collection data (including `bin_schedule`) and running the
[bin population](#bin-population-residents-per-bin) command:

```bash
docker compose exec backend uv run python -m app.interfaces.bin_days --start 2026-09-09 --end 2026-10-09
# native, from backend/
uv run python -m app.interfaces.bin_days --start 2026-09-09 --end 2026-10-09
```

The current exports give 31 days × 21,695 bins = 672,545 rows. Options (all optional):
`--seed` (42), `--p-first` (0.028), `--p-retry1` (0.40), `--p-retry2` (0.70) and
`--holiday-factor` (2). Probabilities must be in [0, 1] and the factor at least 0. The
summary prints the seed, the parameters and the number of rows per status. The simulation
runs in plain Python, so long ranges take a while: 31 days take about 20 s and one year
(2026-10-10..2027-10-09, about 7.9M rows) about 4 minutes. The five-year maximum would take
roughly 20 minutes.

Every column (type, nullability, meaning, values, and whether it is copied, estimated or
synthetic) is described in [`bin_days` columns](docs/bin-days-columns.md).

- **Which bins:** a bin gets a row for every date when it has a `sub_district` and at least
  one stored planned date. Others are skipped and counted in the summary as excluded
  without sub-district or without schedule.
- **Replacement:** each run replaces the whole table in one transaction, and a failure leaves
  it unchanged. Both dates are required, and ranges longer than five years (1,827 days) are
  rejected. Exit codes: 0 on success, 1 on invalid arguments or failure.
- **Assumptions:**
  - Attributes are a snapshot from the time of the rebuild, applied to every date.
  - Bins have no install or removal dates, so every included bin is assumed to exist on
    every day.
  - ISO weeks near New Year can belong to the neighbouring year (2027-01-01 is week 53).
  - The stored schedule (the latest monthly snapshot) repeats unchanged over the whole
    range. Its cycle is the shortest of 1, 7, 14, 21 or 28 days that reproduces the stored
    dates; a single stored date means every 28 days, and irregular dates fall back to 28.
  - A collection is attempted on every planned day. A failed attempt is retried on the next
    day and, if that fails, once more on the day after. A planned day cancels a pending retry.
  - The failure probabilities are assumptions, not fitted values. For reference, 3.4% of
    `bin_hist` events are non-serviced (including reasons that are not carrier failures),
    and 23% of next-day events after a non-service are non-serviced too. Holidays multiply
    the probability by the factor, capped at 0.95. With the defaults a planned collection is
    missed with probability 0.028 × 0.40 × 0.70 ≈ 0.78%. The observed share is higher: about
    1.0% for non-daily bins (holidays raise it) and 1.8% overall, because a daily bin has
    no retry, so any failure is a miss (2.8%).
  - Holidays do not move collections. They only raise failure probability.
  - The simulation starts 35 days before `--start` so the first rows have full 28-day
    features. Output depends on the arguments, so changing `--start` changes the draws.
  - Each bin has its own random stream (`seed` and `bin_id`), so the same arguments give
    identical output regardless of other bins.
- **Keeping it in sync:** a deleted bin loses its rows. A CSV import that replaces `bins`
  empties the table, so rerun the command afterwards (after the bin population command). Refreshing `bin_schedule` does not
  change existing rows until the next rebuild.

See [bin-day calendar verification](docs/bin-day-calendar-verification.md) for repeatable checks.

## Truck management

Open `/` and choose `Administratorius` to enter `/admin/trucks`. The supplied Vilnius logo is centered near the top, above the VipTop leaf branding and role selection. `Vairuotojas` is a disabled placeholder. Admin access requires no authentication. The shared navbar shows a compact Vilnius logo on the right and VipTop on the left; both branding links lead back to `/`. It links to `Šiukšliavežės`; below 640 pixels, links collapse into a hamburger menu. Its labeled toggle supports keyboard opening, selection closes the menu, and Escape closes it and returns focus to the toggle.

The screen supports name search, availability, waste carrier and inclusive volume filters, with at most 10 trucks per page, previous/next controls and a page-number input submitted with Enter or `Eiti`. Filter changes reset to page 1. The always-visible, right-aligned action row above the table contains equally sized `Pridėti šiukšliavežę` then the filled `Išvalyti filtrus` button. The add button opens the same form used for editing a row; new forms default to available, with blank volume and carrier selection. Maximum capacity is waste volume in m³; fractions are supported. Delete requires confirmation and retains the truck row without changing collection history. Successful CRUD refreshes the whole-fleet overview and current filtered page, recovering to the last valid page if needed, without a full page reload.

Create/edit success appears as `Šiukšliavežė išsaugota.` in a toast entering from the top right; failed save requests show an error toast while preserving entered values. Field validation stays beside inputs. Toasts support accessible announcements, labeled dismissal, reduced motion and automatic dismissal, and remain visible above open dialogs. Read refresh failures retain their own retry controls; retrying does not repeat a committed save or its toast.

| API | Behaviour |
|---|---|
| `GET /trucks` | Nondeleted page; optional `name`, `available`, `min_max_volume_m3`, `max_max_volume_m3`, `waste_carrier`, `page` |
| `GET /trucks/stats` | Whole nondeleted fleet: `total`, `available_count`, `average_max_volume_m3` |
| `GET /trucks/{id}` | Nondeleted detail, or `404` |
| `POST /trucks` | Required `name`, `max_volume_m3`, `waste_carrier`, `landfill_id`, `available`; `201` saved truck |
| `PATCH /trucks/{id}` | Partial updates to those five fields; `200` saved truck; missing/deleted ID is `404` |
| `DELETE /trucks/{id}` | Atomic soft deletion retaining landfill; bodyless `204`; missing/already deleted ID is `404` |
| `GET /landfills` | Complete read-only catalog array, ordered by generated ID, with all mapped source fields |

List responses use `{ "items": [...], "total": 21, "page": 1, "page_size": 10 }`. Pages are one-based and default to 1; invalid/nonpositive pages return `422`, while a valid page beyond the results returns empty items with the matching total. Count and items apply the same filters before pagination, ordered by ID. Invalid UI page jumps show a Lithuanian error without fetching; changing/clearing filters resets both the page and page input. Names use trimmed, case-insensitive literal substring matching; filters combine with AND. Blank search has no effect. Volume bounds must be finite numbers greater than zero, with minimum no greater than maximum. Fractions and values above 99 are accepted. Carrier matching is literal equality after trimming; blank carrier has no effect.

The overview above the filters covers all nondeleted trucks independently of table filters/pages: total, average maximum waste volume (one decimal in Lithuanian formatting with m³), and available percentage with a proportional green circular arc. `GET /trucks/stats` returns `{ "total": 21, "available_count": 11, "average_max_volume_m3": 11.0 }` for the synthetic 1–21 m³ example. The average is null for an empty fleet, displayed as — alongside 0 total and 0% availability. Statistics have independent loading/error/retry states; a failed refresh does not undo or repeat a committed mutation.

The screen uses a wider aligned admin layout, neutral gray surfaces and leaf branding. The available/total count beneath `Prieinamos šiukšliavežės` (for example, `24 iš 27`) matches the size and weight of the other overview values; the circular percentage remains beside it or wraps at narrow widths. The volume column is `Maksimali talpa` and displays `18 m³` or `18,5 m³`. The adjacent carrier column is `Atliekų vežėjas`. Truck-specific frontend files live under `frontend/src/pages/trucks/`; shared layout/branding/UI primitives, toast provider and `TablePagination` live under `components/`. Backend HTTP router/schemas live under `app/interfaces/trucks/`; the CLI lives under `app/interfaces/bin_sync/` and keeps the existing `python -m app.interfaces.bin_sync` invocation.

Truck responses expose exactly `id`, `name`, `max_volume_m3`, `waste_carrier`, `landfill_id`, `available`. Mutation inputs trim nonempty names and carrier strings, require positive finite numeric volume and boolean availability, reject explicit nulls, numeric strings/booleans and unknown fields, and permit duplicate names. The removed `max_bins_per_trip` mutation field is rejected. `id`/`deleted` cannot be set by clients. Omitted PATCH fields remain unchanged; an empty patch returns the eligible unchanged truck, including an unassigned one. Create requires a strict positive integer landfill ID that exists; supplied PATCH landfill IDs reject null, strings, booleans, fractions and unknown IDs with field-addressable `422`. A nonempty edit of an existing unassigned truck requires landfill selection; an assigned truck preserves an omitted assignment. Reads return null for transitional unassigned trucks. Validation errors return `422`; persistence failures return generic `500` responses without partial changes.

Create/edit uses `Pavadinimas`, `Maksimali talpa` with a visible `m³` unit,
`Atliekų vežėjas`, `Sąvartynas` and `Prieinamas`. Volume input/filter text accepts decimal
commas or points and sends JSON numbers. Carrier selection offers only
`Kauno švara`, `Biomotorai`, `Ecoservice` and `Ekonovus`; the carrier filter adds
`Visi vežėjai`. The database/API can store and return other nonempty carrier
names. The list displays them faithfully; opening their editor shows the
original name and requires an explicit listed carrier choice before saving,
without silently replacing it. Opening/cancelling never changes a record. The landfill select loads all three exact source names from `GET /landfills`; it starts blank for create/unassigned trucks, preloads assigned edits and sends a numeric ID. Loading/error/empty catalog states prevent saving with Lithuanian feedback and retry, preserving entered values. No landfill is selected automatically.

The browser calls same-origin `/api/trucks` and `/api/landfills`; Vite strips `/api` and proxies to FastAPI. Compose configures server-only `VIPTOP_API_PROXY_TARGET=http://backend:8000`. For native frontend development, the default is `http://127.0.0.1:8000`; override it for a different backend port:

```bash
cd frontend
npm ci
VIPTOP_API_PROXY_TARGET=http://127.0.0.1:8000 npm run dev
```

`npm run build` builds the frontend, and `VIPTOP_API_PROXY_TARGET=http://127.0.0.1:8000 npm run preview` serves the build with the same proxy. Deep-link open/refresh is supported in development and preview. A future production static host will need an equivalent API proxy and SPA fallback.

## Collection browsing

In the admin navbar, choose `Šiukšlių surinkimo vietos` or open
`/admin/sites`. This screen shows address-grouped sites and their bin
counts, with address search and 15 sites per page. Search is a trimmed,
case-insensitive literal substring match; changing or clearing it resets page 1.
The global site count, bin count, waste-type donut and capacity sum stay
independent of search and pagination. Container totals/category counts sit beside
the donut, with glass green, paper/plastic blue and mixed municipal waste brown.
Each section has its own retry control.
NULL capacity displays `N/A`; known zero displays `0 m³`. The capacity unit is
the existing **unverified assumption**, without conversion of stored values.

| API | Behaviour |
|---|---|
| `GET /sites` | `{items: [{id, address, bin_count}], total, page, page_size}`; optional `address`, `page` and `page_size` |
| `GET /sites/stats` | `{total_sites, total_bins, total_capacity_m3, bins_by_waste_type: [{waste_type, count}]}` for the entire registry |
| `GET /sites/{id}` | Site identity/address/coordinates, first-bin location text and all-bin count/capacity/groups/carriers; missing parent returns 404 |

Pages default to 1 and site page size to 15 (allowed 1–100). Invalid parameters
return 422; valid pages beyond the results return empty items with correct totals.
Capacity is a JSON number or null. Waste-type keys preserve source text; known
labels are translated only in the UI. Each request uses its own short read-only
snapshot, with a five-second statement timeout and one-second lock timeout.
Separate requests can observe different committed import progress.

Rows open `/admin/sites/{id}`, also accessible directly or after refresh. Details
show a street map that supports dragging, wheel/touch/keyboard movement and
zooming, with `Priartinti`/`Atitolinti` buttons, plus compact site statistics. The stored location
is an arithmetic average of member-bin coordinates, not a surveyed entrance.
`sub_district`, `street`, `house_number` and `postal_code` all come from the
lowest internal `Bin.id`; a NULL is never filled from another bin. House numbers
and postal codes retain text formatting. `bin_count`, `total_capacity_m3`,
`object_groups` and `waste_carriers` cover every child; distinct non-NULL groups
and carriers are sorted. Details contain no nested bins/history. Empty sites
remain available with count 0, null capacity/location text and empty arrays.
Missing values display `N/A`. Map failures have their own retry and leave site
statistics usable. Paginated child bins open their service-history dialog.

Docker Compose passes `VITE_MAP_STYLE_URL` to the frontend, defaulting to
`https://tiles.openfreemap.org/styles/liberty`. Override it in the root `.env` or
shell before starting/recreating the frontend. Vite reads the variable at startup;
the map component has no hardcoded fallback.

For native development, configure `frontend/.env.local` and use the real backend
on port 8000:

```bash
cd frontend
test -f .env.local || cp .env.example .env.local
npm ci
VIPTOP_API_PROXY_TARGET=http://127.0.0.1:8000 npm run dev
```

Packaged builds embed the map URL at build time:

```bash
VITE_MAP_STYLE_URL=https://tiles.openfreemap.org/styles/liberty npm run build
VIPTOP_API_PROXY_TARGET=http://127.0.0.1:8000 npm run preview
```

A missing/invalid map configuration displays a Lithuanian map error while site
statistics and bins remain usable. See
[collection browsing verification](docs/collection-site-browsing-verification.md)
for the main Compose read-only checks and recorded verification limits.

## Collection records

A Site groups physical Bins by registered street plus house number, trimmed,
whitespace-collapsed and case-folded. `site_key` is unique (`address:<normalized>`
or isolated `unknown:<external_id>`). Display addresses remain readable.
Distance and client addresses do not determine membership. Site coordinates
are arithmetic averages of all current members, including out-of-bounds bins
retained from earlier imports; they are not surveyed entrances. Truck capacity is
maximum waste volume in m³; collection-site counts no longer describe truck capacity.

| Table | Fields |
|---|---|
| `sites` | `id`, `site_key`, `address`, `latitude`, `longitude` |
| `bins` | `id`, `site_id`, `external_id`, `inventory_number`, `waste_type`, `capacity_m3`, `latitude`, `longitude`, `district`, `region`, `sub_district`, `city`, `street`, `house_number`, `postal_code`, `territory_type`, `object_group`, `waste_carrier`, `client_count` |
| `bin_hist` | `id`, `bin_id`, `date`, `was_serviced`, `non_serviced_reason`, `fill_level` |
| `trucks` | `id`, `name`, `max_volume_m3`, `waste_carrier`, `landfill_id`, `available`, `deleted` |
| `landfills` | `id`, `source_id`, `dataset_name`, `dataset_description`, `latitude`, `longitude`, `name`, `operator`, `address`, `facility_role`, `waste_streams`, `status`, `coordinate_quality`, `coordinate_source`, `facility_source`, `municipal_arrangement_source`, `current_status_source`, `verified_at` |

Truck volume is required positive finite NUMERIC and permits fractions without
the old 99 limit. Truck carrier is required TEXT without an enum, allowed-value
check or catalog relationship; future company names can be stored. Truck IDs
retain their generated integer identities. `landfill_id` is a nullable INTEGER
foreign key with restricted deletion of referenced landfills; NULL is retained
for trucks predating assignment support.

Landfills are seeded once from `vilnius_waste_facilities.geojson` in migration
`0006`: three generated INTEGER IDs 1–3 in file order; the next is 4. Original
feature IDs are `source_id`, GeoJSON longitude/latitude are separate DOUBLE
PRECISION columns, and collection name/description are repeated as dataset
metadata. All properties are retained: text, ordered `waste_streams TEXT[]`,
`verified_at DATE`, and NULL for absent source URLs. All `type` fields are
omitted. The migration embeds the data and requires neither Downloads nor
network access. Supplied facility status, coordinate quality and verification
dates are provenance from the file, not independently verified route facts.
At revision `0007`, only generated `id` and dropdown `name` are required.
Source IDs, dataset metadata, coordinates and all other facility details may
be NULL; the lookup returns these as JSON null. Nonnull source IDs remain unique
and provided coordinates still obey geographic range checks. The original seed
values and required Truck selection are preserved.
See [Truck verification](docs/truck-management-verification.md) for the exact
source hash, mapping and guarded upgrade/rollback procedure.

Collection IDs are generated BIGINT identities. The unique `bins.external_id`
retains VASA identity when present; manual Bins use NULL, with uniqueness retained
for non-NULL IDs. Required Bin fields are site, waste type and
coordinates; all other attributes are nullable. Site fields are required.
Geographical/descriptive attributes are TEXT, including house numbers and postal
codes. Preserve source formatting: a bin's `8303` is not replaced with a client's
`08303`. `client_count` counts address-list entries, not residents: valid empty
lists give 0 and missing/malformed lists give NULL. `capacity_m3` is NUMERIC and
stores raw volume unchanged; cubic metres remain an **unverified assumption**.

Bins have no service snapshot fields. History stores actual attempts from the
history endpoint, including failures, naive wall-clock timestamps without UTC
assignment, and source reasons (including empty strings). `fill_level` is NULL
or SMALLINT 0–3; newly imported attempts have NULL, and later observations survive
refresh. History is unique by `(bin_id, date, was_serviced)`: distinct attempts
sharing all three values can collapse, while different statuses at one timestamp
coexist. Events missing from a refresh remain while their bin exists. No truck,
route, duration, synthetic fill, prediction or historical location is inferred.

Deleting a Site cascades to its Bins and their history and resident requests.
Removing a Bin cascades to its history and resident requests; deleting its final
Bin through the admin API also removes the Site. Truck retirement retains the row, sets deleted
true/available false, and leaves all collection data unchanged.

```sql
SELECT count(*) AS stored_sites FROM sites;
SELECT id,site_key,address,latitude,longitude FROM sites ORDER BY id LIMIT 10;
SELECT id,external_id,site_id,postal_code,client_count FROM bins ORDER BY id LIMIT 10;
SELECT h.id,h.date,h.was_serviced,h.non_serviced_reason,h.fill_level
FROM bin_hist h JOIN bins b ON b.id=h.bin_id
WHERE b.external_id=135353 ORDER BY h.date,h.id;
SELECT id,phase,diagnostics FROM vasa_import_runs ORDER BY id;
SELECT run_id,kind,complete,count(*) FROM vasa_import_progress
GROUP BY run_id,kind,complete ORDER BY run_id,kind,complete;
```

## Bin synchronization

The manual module command uses VASA `/api/cluster/{z}/{x}/{y}` MVT tiles and the
configured bin-detail and paginated history endpoints. It imports only Mixed
municipal waste, Paper/plastic waste, and Glass waste; excludes normalized
Individualios valdos; retains only missing or Vilnius city names; and filters
individual point coordinates to the configured bounding box. Tiles use their
own extent and the decoder's Y-up orientation. Missing geographical property
keys trigger a detail request; explicit NULL alone does not. Detail attributes
are authoritative, coordinates stay from the tile, and filters are reapplied.

| Option | Default / meaning |
|---|---|
| `--bbox WEST SOUTH EAST NORTH` | `24.98 54.55 25.52 54.85`; inclusive point bounds |
| `--zoom` | 17; aggregate-only tiles cannot establish physical coverage |
| `--workers` | 4; positive maximum concurrent requests |
| `--max-sites` | 10; 0 means unlimited |
| `--max-tiles` | 0 means unlimited |

Any nonzero limit is an incomplete trial, even when fewer results exist. Selected
addresses may have unseen member bins. Limits and worker count can change while
resuming the same scope. Bounds, zoom, URLs, filter and mapping versions define
compatible coverage. An unlimited continuation revisits partial tiles and admits
omitted records. The importer has no CSV output or distance grouping option.

Each tile, required detail response, and history page commits its data and
checkpoint together. A single database writer recalculates affected site means;
network work uses bounded futures. Histories persist page by page rather than
accumulating a bin's complete history. Short/empty pages advance when metadata
indicates continuation. API links are never followed; the next page is fetched
on the configured HTTPS endpoint. Unexpected 404s and malformed essential values
leave work incomplete. Transient requests have five attempts with exponential
backoff capped at 20 seconds; pagination is limited to 10,000 pages. Detectable
pagination changes restart that bin's retrieval, retaining stored events. VASA
has no verified frozen snapshot token, so resumed traversal is best effort.

Only full successful tile/detail/history coverage allows cleanup. In one final
transaction it removes unseen bins whose **stored individual coordinates** lie
inside the refresh bbox, cascades their history, removes newly empty affected
sites, recalculates surviving means over every remaining member, and marks the
pass complete. Out-of-bounds bins/history survive. A verified empty full pass
can remove all in-bounds bins. Failed cleanup rolls back deletion and completion
together; rerunning retries finalization. Trials/errors never clean up.

A nonblocking PostgreSQL advisory lock rejects a second simultaneous importer.
The lock and importer engine belong to the command and are released on exit;
separately running import work does not delay backend shutdown.

| Environment setting | Configuration |
|---|---|
| `DATABASE_URL` | Required `postgresql+psycopg` connection |
| `VASA_TILE_URL_TEMPLATE` | HTTPS template with `{z}`, `{x}`, `{y}`; example default |
| `VASA_BIN_URL_TEMPLATE` | HTTPS template with `{external_id}`; example default |
| `VASA_HISTORY_URL_TEMPLATE` | HTTPS template with `{external_id}`; example default |
| `BIN_SYNC_HTTP_TIMEOUT_SECONDS` | Required positive finite socket timeout; example 30 |

Database connections time out after 10 seconds; importer transactions use a
30-second statement timeout and 5-second lock timeout. HTTP timeout is socket
inactivity per attempt, not a whole-import deadline. Native commands run from
`backend/` with an accessible exported connection, e.g.:

```bash
uv run python -m app.interfaces.bin_sync --max-sites 10
uv run python -m app.interfaces.bin_sync --max-sites 0 --max-tiles 0
# A narrower refresh uses separate coverage; adjust bounds to the intended area.
uv run python -m app.interfaces.bin_sync --max-sites 0 --max-tiles 0 --bbox 25.2961 54.70245 25.2964 54.7026
```

A trial exits 2 and never removes missing bins. Matching incomplete runs resume.
After full success (exit 0), the next invocation starts a fresh refresh. Failures
exit 1 and retain already committed progress. In Docker, prefix the commands with
`docker compose exec backend`.

## Collection schedules

`bin_schedule` holds VASA's planned collection dates per bin (one row per bin and
date). They are VASA's plan, not observed service history. Load collection data
first (CSV import or `bin_sync`), then run:

```bash
docker compose exec backend uv run python -m app.interfaces.bin_schedule_sync --max-bins 20
docker compose exec backend uv run python -m app.interfaces.bin_schedule_sync
# native: run the same command from backend/ without the docker prefix
```

- **Options:** `--workers N` (default 4) bounds concurrent requests; `--max-bins N`
  (default 0 = all) processes only the first N bins by ID.
- **Manual bins:** bins with NULL external IDs are excluded before applying
  the limit; they have no VASA identity and are never sent to the source API.
- **Exit codes:** 0 when every bin was processed without failure; 1 on any failed bin,
  invalid arguments or configuration, or no stored bins; 2 for a `--max-bins` run
  without failures.
- **Snapshot:** VASA only returns the current month. Each successful response replaces
  that bin's stored dates, so the table holds the latest fetched month only. A failed
  bin keeps its previous dates and its external ID is listed (first 20) in the summary.
  Re-run at the start of each month; consumers should filter on `date >= today`.
- **Empty lists:** VASA returns an empty list both for a bin without a plan and for an
  unknown ID, so the summary reports the empty count; a sudden jump points to a source problem.
- **Duration:** a full run takes about 13 minutes for ~22k bins with 4 workers.
- **Import side effect:** a CSV import that replaces `bins` empties `bin_schedule`; see
  [Import table CSV exports](#import-table-csv-exports).

## Migration and verification

From `backend/`, with the accessible `DATABASE_URL` exported:

```bash
uv sync --locked
uv run alembic upgrade head
uv run alembic check
```

Revision `0004` replaces the legacy collection tables in dependency order,
creates sites, physical bins, history and internal `vasa_import_runs` /
`vasa_import_progress`, and retains trucks. Historical revisions `0001`–`0003`
are unchanged. Upgrade performs no source I/O. Repeated upgrades preserve new
records. Downgrade through `0004` is unsupported: the migration reports that a
pre-upgrade backup must be restored or disposable storage recreated. Discarded
records cannot be reconstructed by downgrade.

Rebuild the backend with `docker compose up --build` to package the new revision
and dependencies. Its entrypoint upgrades before serving but never imports.
Revision `0013` permits NULL Bin external IDs and cascades Site deletion to its
Bins; it follows main's population migration `0012` without changing its schema.
Follow [data verification](docs/data-foundation-verification.md) and
[truck verification](docs/truck-management-verification.md) on disposable data.
Earlier revision-specific results there are historical evidence.

### Child containers and service history

Site details include a read-only bin list (10 per page). Select a container for
its inventory number, Lithuanian waste label, capacity and service history. The
wide dialog shows date, status, reason and fill in one row per attempt, with
horizontal scrolling on narrow screens. It shows the all-history successful-service percentage
and newest-first attempts (20 per page),
raw fill values 0–3, `N/A` for NULL, and stored wall-clock times across timezones.
Closing returns focus to the selected row; reopening starts history at page 1.
Bins, history and site details have independent retry.

`GET /sites/{id}/bins` accepts positive `page`/`page_size` (default 10, max 100);
`GET /bins/{id}/history` defaults to/maximizes at 20. Both return `items`, `total`,
`page`, `page_size`; history also returns `successful_service_percentage` and
`unsuccessful_service_percentage` over all stored attempts. Missing parents return
404, invalid parameters 422; valid out-of-range pages are empty. No-history
percentages are null.

See [collection browsing verification](docs/collection-site-browsing-verification.md)
for repeatable GET/read-only SQL comparisons, timezone checks and synthetic versus
unmet real-storage evidence. Collection browsing now runs from the main checkout
with `docker-compose.yml`.

All lists (sites, bins, history and trucks) show pagination only when a known
total exceeds page size. Empty, single-page and pending lists hide the controls.

## Collection-site management

At `/admin/sites`, choose `Pridėti surinkimo vietą` beside the address search. Enter street, sub-district
and house number, optionally a postal code, select a location, and define one or
more containers. The map title asks you to select a location by clicking. Disabled, nonselectable
latitude/longitude fields below the map start empty and update
when a point is selected. Click the map, or focus it, pan with the arrow keys and
press Enter/Space to select its center; the initial Vilnius view does not count.
Only the disabled coordinate fields appear below the map; no selection buttons
or helper text are shown there.
The modal scrolls within the viewport. Cancel saves nothing; failures retain
inputs. Successful creation refreshes the current filtered list and global
statistics without reloading.

Every new container requires `Naudotojai` (`object_group`, descriptive text),
inventory number, capacity, carrier and waste type. Capacity is a positive finite
JSON number in m³; decimals are supported without a fixed upper bound or display
rounding before persistence. Carriers are Kauno švara, Biomotorai, Ecoservice and
Ekonovus. Waste selections map to the existing English storage values.

```json
{
  "street": "Didlaukio g.",
  "sub_district": "Verkių sen.",
  "house_number": "53A",
  "postal_code": "08303",
  "latitude": 54.72,
  "longitude": 25.28,
  "bins": [{
    "object_group": "Gyventojai",
    "capacity_m3": 1.1,
    "waste_carrier": "Ecoservice",
    "inventory_number": "MANUAL-1",
    "waste_type": "Glass waste"
  }]
}
```

`POST /sites` returns 201 `{id, address, bin_count}` after committing the Site
and all initial Bins together. The example address is
`Didlaukio g. 53A, Verkių sen., 08303`. Blank/omitted/NULL postal code stores NULL;
house and postal numbers remain text. The server generates `manual:<UUID>` keys:
creating at the same address makes a separate Site. Each Bin copies the selected
location/address and receives NULL external identity, territory and client count,
plus district `Vilniaus m. sav.`, region `Vilniaus apskr.` and city `Vilniaus m.`.
History and resident requests start empty. Invalid inputs return 422; persistence
failures return a generic 500 and roll back the entire operation.

Imported locations are derived means during import; manual Site locations are
explicit selections. Admin additions/deletions preserve surviving stored Site
locations. Viewing a map does not change either kind of location. The new input
rules preserve legacy nullable attributes and unrestricted source values.
See [management verification](docs/collection-site-management-verification.md)
for disposable API/SQL checks and recorded UI evidence.

At Site details, `Pridėti konteinerį` opens just the five container fields.
`POST /sites/{site_id}/bins` takes one Bin definition (the `bins` item above)
and returns 201 `{id, inventory_number, waste_type, capacity_m3}`. It copies the
Site's coordinates and all four address fields from the same lowest-ID child,
including NULLs. A legacy empty Site supplies NULL address fields; its display
address is not parsed. The refreshed list opens the last ascending-ID page so
the new Bin can be inspected, with empty history until actual records exist.

Truck, Site and Bin rows share the same small red ghost-style `Ištrinti` control.
Site list rows show street and house number; full addresses remain in details,
confirmation and API responses, and address search still uses the full address. Confirmation identifies
the record and explains permanent removal of history and resident requests.
`DELETE /sites/{site_id}` returns bodyless 204 after cascading deletion.
`DELETE /bins/{bin_id}` returns 200 `{site_id, site_deleted}`; deleting the final
Bin removes its Site in the same transaction and returns to `/admin/sites`.
Successful deletions refresh lists/statistics and recover the last valid page
under the current filter. Missing positive IDs (including BIGINT overflow) return
404; nonpositive/noninteger IDs return 422. Missing UI records offer a read refresh
or navigation back. Refresh retries do not repeat successful mutations. Adding
or deleting children locks the Site first, keeping concurrent final-child changes
consistent. Deleted imported records can reappear after a future explicit import;
manual NULL-ID Bins are excluded from importer cleanup.

## Map analytics

Choose `Žemėlapio analitika` in the admin navbar or open `/admin/map-analytics`.
The large Vilnius map fills the content width. One card underneath contains
`Sluoksniai` and name-only checkboxes, then `Legenda` and labeled color swatches.
Long layer lists scroll internally. Clicking the map does not draw a focus
outline; keyboard interaction retains visible focus.
Check `Sąvartynai` to load the existing three-facility catalog, explore clustered
counts, click clusters to zoom in and click individual points for recorded details.
The layer starts unchecked; successful data is reused until leaving the page.
Toggles preserve the view. Dataset retry and map recovery are independent.
The `Legenda` section lists registered color meanings:
landfill pins and clusters are green. Definitions can supply multiple categories
and feature-based point colors; the same legend metadata supports future
non-point renderers. Facility popups show the name as a heading and only operator
and address rows.

`GET /map-analytics/landfills` (browser: `/api/map-analytics/landfills`) returns a
GeoJSON FeatureCollection ordered by landfill ID. Points use `[longitude,
latitude]` and only `name`, `operator`, `address`, `coordinate_quality` properties;
null coordinates omit the feature, while null details remain null (`N/A` in the
popup). The catalog endpoint `/landfills` retains its existing contract. This
feature adds no migrations or data imports.

Analytics uses the same `VITE_MAP_STYLE_URL` startup/build setting as site maps,
with no component fallback. The configured style must support the cluster-count
font (`Noto Sans Regular` by default). Known English seed descriptions are shown
in Lithuanian without changing stored data; recorded approximate coordinates
remain approximate. For native development, start this checkout's backend and run:

```bash
cd frontend
VITE_MAP_STYLE_URL=https://tiles.openfreemap.org/styles/liberty \
  VIPTOP_API_PROXY_TARGET=http://127.0.0.1:8000 npm run dev
```

See [map analytics verification](docs/map-analytics-verification.md) for read-only
API commands, the three-facility walkthrough, acceptance status and instructions
for adding point definitions or future non-point renderers to the common registry.
