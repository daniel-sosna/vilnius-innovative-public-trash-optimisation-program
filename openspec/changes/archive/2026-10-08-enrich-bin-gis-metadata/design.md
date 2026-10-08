# Design

## Context

See [proposal.md](proposal.md) for motivation and compatibility changes. Contracts are in the [collection-records delta](specs/collection-records/spec.md) and [bin-synchronization delta](specs/bin-synchronization/spec.md). Governance remains in [openspec/config.yaml](../../config.yaml).

Revision `0001` establishes the five collection tables; additive revision `0002` and the current ORM add the two optional Bin metadata columns. The GIS client now retains the configured query and maps all six Bin attributes; the service fetches completely before its one transaction and writes in batches of 1,000. Both continuation-flag locations and Polygon/MultiPolygon geometry remain supported. The completed metadata work does not need another schema revision.

Settings live in `backend/app/core/config.py` and currently load the shared repository-root dotenv with environment precedence. The root `.env.example` includes PostgreSQL container keys alongside the backend connection and synchronization keys. Pydantic settings and python-dotenv are already locked dependencies. The current FastAPI lifespan creates database resources solely for an initial import, followed by a sequential background timer and a stop-event shutdown wait. `app.interfaces.bin_sync` already exposes a complete single-run command that owns and disposes its database engine. `start.sh` already applies Alembic migrations before executing Uvicorn.

Exploration verified the supplied 50-feature URL and the full source domain. Both metadata fields contain integer codes or null, and the current non-null values are recognized. Many null values are normal source data; they are not invalid-site evidence. The source advertises a 2,000-record limit and pagination support.

## Goals / Non-Goals

**Goals:** Preserve the metadata import path, make its execution explicitly operator-controlled, and keep startup schema preparation independent of GIS availability. Keep source translation distinct from unrestricted storage and configuration resolution consistent across the migration and import entry points.

**Non-Goals:** Classification entities, raw-code columns, dynamic domain discovery on every import, scheduling infrastructure, automatic import flags or persistent import markers, manual-edit protection, new indexes for hypothetical filters, separate services, and changes to unrelated entities.

## Decisions

### 1. Add nullable text through a new migration

Add `type` and `greening` as `Mapped[str | None]` with PostgreSQL `TEXT`. Create revision `0002` following `0001`, adding only these two nullable columns without defaults, data conversion, checks on labels, or new indexes. Keep the original revision unchanged. Existing rows naturally receive null; no GIS request belongs in a migration. Downgrade to `0001` drops only the new columns, losing their values while retaining the original records and references.

Alternative: enums/check lists or classification foreign keys would contradict the free-text requirement. Changing revision `0001` would not migrate databases that already applied it. Nullable additive columns avoid invented metadata and allow an unavailable source after upgrade.

### 2. Translate optional source codes in the existing mapper

Keep the ten-entry type mapping and three-entry greening mapping as explicit constants in `app/integrations/vilnius_gis.py`, using the exact labels in the spec. Extend `BinValues` and the returned dictionary with both nullable text keys. Storage accepts arbitrary text, while this importer translates the observed numeric source contract.

Use strict integer-code lookup; booleans, floats, numeric strings, and other non-null shapes are not coerced into recognized codes. Missing/null values map to null silently. For an unknown or unusable non-null code, warn with Bin ID, source field, and raw value, then return null for that field. Keep the otherwise valid feature: these warnings neither increment `skipped` nor alter successful command exit status. Required identity/geometry checks still determine whether the whole feature is skipped.

Alternative: storing unknown numbers as text was explicitly declined. Failing a complete import or skipping the site for optional metadata would unnecessarily discard valid identity/location data. Fetching classification metadata on every explicit import adds an external dependency for mappings already supplied and confirmed.

### 3. Preserve the configured query while owning pagination

Set `.env.example`'s source value to the user's full query URL:

```text
https://opencity.idvilnius.lt/gis/rest/services/Miesto_tvark/Miesto_tvarkymas_public/MapServer/29/query?f=geojson&resultOffset=0&resultRecordCount=50&where=1%3D1&outFields=%2A&returnGeometry=true&outSR=4326&spatialRel=esriSpatialRelIntersects
```

Parse the URL query once. Preserve its query parameters, including all-fields selection, spatial relation, and the requested page size; apply only the client's pagination offset and stable `OBJECTID ASC` ordering. Start at zero, even if a configured offset is nonzero, to maintain the complete-registry contract. Increment by the requested page size when either continuation location is true, including after short or empty pages.

For existing bare query endpoints used in manual fixtures, retain a focused default query using the current 1,000-record size, `where=1=1`, GeoJSON, geometry, output reference 4326, and the new `outFields=*`. Overlay a supplied query rather than discarding it. The supplied production URL therefore uses 50; HTTP page size and the existing 1,000-row database batch size are independent. Validate the effective page size as an integer between 1 and the existing 1,000-record retrieval size before fetching. This conservative supported range is below the observed 2,000-record server limit: a request larger than the server permits could otherwise return a truncated page and skip sites when advancing offsets. Reject unsupported sizes with a workflow error and retain stored data. This supports the supplied source and existing controlled-input commands without adding another environment setting, additional metadata lookup, or general GIS configuration layer.

Keep descriptive headers, timeouts, collection validation, duplicate-ID rejection, and coordinate rules. Ignore unneeded returned properties such as `ETAPAS` and `VIETOS_TIKSLUMAS`. Domain-required GeoJSON/geographic output remains the supported contract; do not claim support for arbitrary layer formats or coordinate systems.

Alternative: importing just the literal first-page URL would truncate the registry. Reconstructing every query unconditionally would continue hiding the requested fields. Selecting four attributes instead of `*` could reduce payload but would depart from the supplied query unnecessarily.

### 4. Expand the existing atomic upsert ownership

Include `type` and `greening` in inserts and the conflict update set. Null is authoritative for a usable source feature and clears a prior known value, including after an unknown replacement code. Absent or skipped sites retain every previous value. Metadata updates must not modify any operational table or references.

Keep the fetch-first transaction, write batching, finite database timeouts, and summary contract. A failure on a later page or database batch preserves all five previously synchronized attributes, including new metadata. GIS synchronization can overwrite manually entered free text; a metadata editing feature and precedence policy are outside this change.

Alternative: preserving old metadata whenever the source now supplies null would obscure the current source state and differ from the existing authoritative-address policy. Separate transactions for metadata could leave mixed versions after failure.

### 5. Require configured values and load the shared root dotenv file

Require the source URL and HTTP-timeout fields without runtime defaults, retaining URL validation and positive finite-timeout validation. Delete the interval field and its validation entirely; there is no scheduler configuration. Keep `DATABASE_URL` required and the existing psycopg validation and credential-safe settings representation. Resolve the local repository-root `.env` from the settings module's location, not the process working directory; use UTF-8 and `extra="ignore"` so unrelated PostgreSQL keys do not invalidate the shared file. Use normal pydantic-settings precedence: process environment overrides dotenv.

For the current repository layout, resolve the root using `Path(__file__).resolve().parents[3]` from `backend/app/core/config.py`. In the standalone image the repository dotenv file is absent; supplied environment values are sufficient, and an absent optional dotenv file is not itself an error. Do not copy or mount `.env` into the image merely to make this work. Native commands can override only `DATABASE_URL` to use localhost while taking the synchronization settings from the root file.

Keep the source URL and HTTP timeout Compose substitutions required through `${VARIABLE:?message}` expressions. Delete `BIN_SYNC_INTERVAL_SECONDS` from Compose and `.env.example`, and remove it from current README/manual verification instructions. For an existing operator `.env`, document removing the obsolete line while preserving connection details and other settings; legacy unrelated keys remain ignored. Existing database/container fallback settings are outside this change. Keep the timeout example at 30 seconds and document creating the local file before Compose startup, or supplying equivalent environment values. Missing required configuration fails clearly rather than falling back silently. Alembic retains the shared Settings class, so migration entrypoints still require the source URL and HTTP timeout as configuration, but never contact GIS. Do not introduce a separate settings hierarchy for this revision.

Alternative: `env_file=".env"` alone would search the native working directory and miss the root file when running from `backend/`. Manual shell sourcing would duplicate setup across entry points. Retaining Compose sync fallbacks would still hide missing inputs after Python defaults were removed.

### 6. Import only through the existing operator command

Remove the import-owned FastAPI lifespan entirely, including its initial attempt, timer, `periodically` coroutine, stop event, thread dispatch, shutdown wait, and database engine/session setup used only by that import. The current application can use a plain FastAPI instance because that lifespan has no other responsibility. Do not replace it with a different lifecycle hook or trigger. Startup, restart, development reload, and idle runtime make no GIS requests; shutdown has no import work to await.

Keep `backend/start.sh` responsible only for `uv run alembic upgrade head` followed by the requested server command. Neither migrations nor this entrypoint import sites. Schema failure still prevents serving. Empty storage remains empty after successful startup until the operator runs:

```bash
docker compose up --build -d
docker compose exec backend uv run python -m app.interfaces.bin_sync
```

The documented native sequence is to configure the accessible connection and root dotenv, apply `uv run alembic upgrade head`, start Uvicorn, then invoke `uv run python -m app.interfaces.bin_sync` from a separate terminal in `backend/`. A built image uses the same module command with the required environment values and reachable migrated storage. No duplicate wrapper script, API endpoint, or alternate import path is needed.

Each invocation imports all indicated pages once and exits; it is not a one-page fetch or a permanently single-use command. Deliberate reruns retain the existing idempotent upsert semantics. The command already owns its database engine and disposes it on success or failure, logs the summary, and returns meaningful exit codes. A separately launched import process is independent of the application process: backend shutdown does not wait for or manage it. The command retains responsibility for atomic publication and its own cleanup. Source failure affects only the explicitly requested run and leaves stored data intact; no automatic retry or next attempt is scheduled.

Alternative: running imports from the container entrypoint would still import on each container restart and couple application readiness to GIS. A database-empty check would silently fetch on first startup and add hidden behavior. Removing all repeat imports or persisting a once-only flag would obstruct legitimate explicit refreshes without satisfying an additional requirement.

### 7. Give third-party integrations a focused package

Move the existing client, feature mapping, mapping constants, and snapshot/value contracts together from `app/infrastructure/vilnius_gis.py` to `app/integrations/vilnius_gis.py`. Update the service import and documentation/module paths. Retain `database.py` and `models.py` in `app/infrastructure/`, the atomic synchronization workflow in `app/services/`, and the operator command in `app/interfaces/`.

This is a package relocation within the current application, with no new dependency, deployment boundary, base adapter class, or compatibility wrapper at the old path. The shared internal import path changes; the externally invoked module command and its data/exit contracts remain the same. Verify the relocated module is included by the existing Docker image's app copy.

Alternative: `clients/` or `adapters/` can express similar responsibilities, but `integrations/` matches the requested boundary and makes third-party ownership explicit without reshaping persistence or application workflows.

## Risks / Trade-offs

- [Unknown future codes lose their uninterpreted numeric value] -> Apply the confirmed null-plus-warning policy; logs identify the raw value and a future mapping change can repopulate it.
- [Free-text storage permits values outside GIS labels] -> This is intentional; translation belongs to import, not a database enumeration.
- [50-record pages increase explicit-command runtime] -> Keep bounded individual HTTP/database operations; document that the socket timeout is not a whole-import deadline. Application readiness and shutdown no longer depend on GIS import latency.
- [Source changes during pagination can affect completeness] -> Retain stable ordering and duplicate rejection; local publication remains atomic without claiming an upstream transactional snapshot.
- [Shared migration settings still require import configuration] -> Keep the source URL and HTTP timeout documented alongside the connection, with no GIS request during migration; validate missing-value diagnostics and the environment-only image path.
- [The root example's `db` hostname is container-specific] -> Document a native localhost `DATABASE_URL` override; keep environment precedence intact.
- [An operator omits population or the source is unavailable] -> The application serves an empty or previously stored registry without fallback data. Document the post-startup import command; a later explicit successful run can populate metadata.

## Migration Plan

1. Keep the completed additive schema and metadata mapping/upsert work. Document creating `.env` when absent and updating its source URL to the supplied full query. Remove the obsolete interval line from example/current instructions; preserve existing operator connection details and unrelated settings.
2. Ship the manual-only application lifecycle, remaining shared configuration, integrations package move, and updated operator documentation together. No additional database revision is needed for this refinement; `0001` and `0002` remain unchanged.
3. Rebuild and recreate the backend. Its entrypoint upgrades the schema and starts request serving without importing Bins. Native operators explicitly migrate before starting the server. Failed migrations still prevent startup.
4. Verify startup, restart, reload, and idle runtime against controlled GIS request capture: no external request or Bin mutation occurs, including when the source is slow or unavailable. Verify normal shutdown without an import timer or wait.
5. Invoke the documented import command once after schema preparation. Inspect complete retrieval, mapped text/null values, atomic publication, and preserved references. Deliberately rerun the command to verify repeatability; changing source fixtures alone must not refresh stored Bins until an explicit run.
6. Verify native, Compose, and image-only paths without an interval setting. Check the image packages both revision `0002` and the relocated integration, and preserves stored raw records through application restarts without refreshing source-owned attributes automatically.
7. Ordinary code rollback may leave the additive columns in place. A deliberate downgrade to `0001` drops only metadata columns and destroys their values; exercise downgrade/re-upgrade only on disposable storage. Import failure never triggers a downgrade.
