# Design

## Context

See `proposal.md` for motivation and `specs/` for behavior contracts. Existing storage is defined in `backend/app/infrastructure/models.py`, with Alembic revisions `0001` through `0003`. Actual obsolete tables are `bins`, `routes`, `route_stops`, and `service_events`. Route stops and events reference bins and routes; routes reference trucks. There are no route/bin HTTP endpoints to remove. Truck services query `Truck` directly and can continue without route models.

The current CLI is `app.interfaces.bin_sync`, delegates to `app.services.bin_sync`, owns its engine, and uses root dotenv settings and psycopg PostgreSQL sessions. Its GIS client accumulates a complete snapshot and publishes one transaction. The supplied `/home/stitas/Desktop/p/venv/vasa_export_address_only.py` already decodes VASA tiles, filters records, normalizes addresses, parses client counts, and traverses history pages, but accumulates all bins/history and writes CSV. The backend currently has neither `requests` nor `mapbox-vector-tile` in its dependencies.

The user supplied a bin detail response from `https://atliekuaiksteles.vasa.lt/vasa-api/api/v1/dumpsters/135353` containing the eight requested geographical attributes. Initial read-only verification returned HTTP 403; implementation preflight with a standard browser User-Agent succeeded. Representative tiles use extent 512 and sometimes omit postal_code, confirming detail fallback. Naive history timestamps and pagination were verified; results are recorded in `docs/data-foundation-verification.md`. Container snapshots and service-history responses are separate inputs.

Main specs describe the old foundation. Completed unarchived `truck-ui` contains current truck retirement requirements and introduces `truck-management`. Merge its specs before this change's deltas; this proposal does not modify or archive that change automatically.

## Goals / Non-Goals

**Goals:** Keep the existing manual entry point and shared database configuration, build a bounded-memory import with atomic response checkpoints, make resume versus refresh explicit in stored pass state, and perform authoritative removal only after complete bounded coverage.

**Non-Goals:** Separate deployments, generic ingestion frameworks, live synchronization, new collection HTTP/UI surfaces, automated test files, restore tooling, provider snapshot guarantees, or data preservation for the deliberately dropped entities.

## Decisions

### 1. Replace collection storage in a new migration, retaining fleet storage

Create a revision after `0003`, provisionally `0004`, rather than modifying historical migrations. Drop `service_events` and `route_stops` before `routes` and old `bins`. Use explicit table drops rather than broad `CASCADE`: unexpected live foreign keys must be identified and resolved deliberately. Keep all truck data, constraints, identity generation, API, and site-count capacity semantics.

Use generated BIGINT identities for Site/Bin/BinHist and the following schema:

| Table | Columns and types |
|---|---|
| `sites` | `id BIGINT PK`, `site_key TEXT UNIQUE NOT NULL`, `address TEXT NOT NULL`, `latitude DOUBLE PRECISION NOT NULL`, `longitude DOUBLE PRECISION NOT NULL` |
| `bins` | `id BIGINT PK`, `site_id BIGINT FK NOT NULL`, `external_id BIGINT UNIQUE NOT NULL`, nullable `inventory_number TEXT`, required `waste_type TEXT`, nullable `capacity_m3 NUMERIC`, required `latitude/longitude DOUBLE PRECISION`, nullable `district/region/sub_district/city/street/house_number/postal_code/territory_type TEXT`, nullable `object_group/waste_carrier TEXT`, nullable `client_count INTEGER` |
| `bin_hist` | `id BIGINT PK`, `bin_id BIGINT FK NOT NULL`, `date TIMESTAMP WITHOUT TIME ZONE NOT NULL`, `was_serviced BOOLEAN NOT NULL`, nullable `non_serviced_reason TEXT`, nullable `fill_level SMALLINT` |

Apply coordinate-range checks to sites/bins, nonnegative nullable client count, `fill_level IS NULL OR fill_level BETWEEN 0 AND 3`, and unique history `(bin_id, date, was_serviced)`. PostgreSQL coordinate checks must also reject nonfinite values. Index `bins.site_id`; the history unique index begins with `bin_id` and supports chronological per-bin queries, so add another history index only if required by the actual access pattern. Configure bidirectional Site/Bin/BinHist relationships. Restrict deletion of sites with bins and cascade Bin deletion to its BinHist children, matching refresh removal. Keep import bookkeeping separate from public domain fields.

Alternative: preserve/reinterpret old site IDs and route history. Rejected because source identities and entity meanings differ and the requested transition deliberately discards that data.

### 2. Keep readable addresses separate from unique normalized identity

Reuse Python `strip`, whitespace collapse, and `casefold` from the supplied script. Join trimmed `street` and `house_number`, normalize the result for `address:<normalized>`, and retain a whitespace-cleaned readable address on the Site. For missing addresses use `unknown:<external_id>` and `Unknown address (<external_id>)`. Do not normalize punctuation, abbreviations, or transliterate Lithuanian text: only the agreed normalization determines identity.

Upsert Site by its unique key and Bin by unique external ID. Keep the first stored readable spelling when equivalent addresses recur, avoiding capitalization changes caused by request order. Compute means with SQL `AVG` across every current stored member of affected sites, including members imported outside the present bounds in earlier passes. On reassignment recalculate both old/new sites and delete newly empty old sites. Duplicate tile observations never count as additional members.

Alternative: store normalized text directly as address or rely on an in-memory map. The chosen internal key preserves display text and database-enforced uniqueness across restarts. Distance functions may order tile requests near the bounding-box center as in the script, but must never group sites; no `--group-radius` is supported.

### 3. Adapt the supplied parser within existing layers

Keep the module CLI under `app/interfaces/bin_sync/` and orchestration/persistence in `app/services/bin_sync.py`; place the VASA network/parsing client in `app/integrations/vasa.py`, replacing the obsolete GIS integration. Reuse the supplied slippy-tile enumeration, per-layer extent, Y-up coordinate conversion, point/physical-bin recognition, filters, address normalization, and client-count parsing. Remove CSV imports, CSV writers, output directories, and `--output`.

Map the exact fields documented in the revised request. Bin has no service snapshot columns: omit `is_serviced`, `service_date`, `last_service_date`, `not_serviced_reason`, `non_serviced_reason`, and `next_service_date`. Do not manufacture a BinHist row from a current container snapshot.

| Source | Destination |
|---|---|
| `id`, `inventory_number`, `dumpster_type` | Bin `external_id`, `inventory_number`, `waste_type` |
| `volume`, tile geometry | Bin `capacity_m3` unchanged, WGS84 `latitude/longitude` |
| bin `district`, `region`, `sub_district`, `city` | matching nullable Bin TEXT columns |
| bin `street`, `house_number`, `postal_code`, `territory_type` | matching nullable Bin TEXT columns |
| `object_group`, `waste_carrier` | Bin text attributes |
| parsed `client_addresses` list length | nullable nonnegative Bin `client_count` |
| `street` + `house_number` | Site address and key |
| history `service_date`, `is_serviced`, `non_serviced_reason` | BinHist `date`, `was_serviced`, `non_serviced_reason` |

Read the eight new fields from the bin's own properties, never from `client_addresses`. Preserve postal codes and house numbers as supplied text: the example's `8303` must not become the client's `08303`, while a supplied leading zero must remain. Missing/null optional values remain NULL. Use the stored Bin street/house-number values to form its Site address and key, applying only the agreed grouping normalization. District, region, sub-district, city, postal code, and territory type do not extend the grouping key.

When any of the eight requested property keys is absent from a tile, fetch the configured bin detail endpoint once per external ID per pass using the same bounded request pool. Explicit NULL keys are known absent values and alone do not trigger fallback. Validate response shape and matching external ID, use returned bin-level properties as authoritative source attributes, retain coordinates from the selected tile, and apply the existing eligibility filters to the resolved record. Missing optional values in a successful detail response become NULL; failed/malformed detail responses remain unfinished work. Container-level `not_serviced_reason` must not substitute for a history event's `non_serviced_reason`.

Parse numeric volume into Decimal without unit conversion. Missing optional values become NULL; malformed optional values produce useful diagnostics and NULL rather than invented zero values. Preserve the distinction between a valid empty client list and an unknown count. Validate BIGINT identity without accepting booleans or silently truncating fractional values. Parse history naive timestamps without attaching UTC; reject unexpected offset-bearing timestamps with a diagnostic rather than silently dropping the offset. The engine's existing UTC session setting does not convert a correctly typed naive history value.

History inserts always supply NULL fill. Conflict updates only change API-owned fields such as the reason; they do not overwrite an existing fill observation. Preserve an API text reason as supplied, including empty text, and preserve NULL as NULL. The composite event key matches available exporter fields and permits separate true/false attempts at one timestamp. Repeated equal keys on a page must be collapsed before batch upsert; prefer a supplied nonempty reason for duplicates on that page, as the reference does. Provider corrections encountered on a later refresh update the source reason; history absent from a refresh is retained while its bin exists because no event-removal policy was requested.

Alternative: introduce an independent standalone script or rewrite the protocol client from scratch. Rejected to keep one supported invocation and preserve working parsing logic.

### 4. Persist pass and work state in PostgreSQL

Use two focused internal tables: `vasa_import_runs` for a generated pass ID, canonical coverage settings/key, phase (`tiles`, `history`, `finalize`, `complete`), and accumulated diagnostics; and `vasa_import_progress` for pass-scoped work records. Give progress a unique `(run_id, kind, work_key)` and a run foreign key. Kinds cover tiles, pending candidates/required detail responses, history pages/bin completion, and seen external IDs; small JSONB details can hold staged mapped attributes, pagination, and selected source-tile information. Detail resolution is part of completing tile discovery before history. These records are internal bookkeeping, not additional bin metadata.

The coverage key includes canonical bbox, zoom, tile/detail/history endpoint URLs, waste/group/city filter version, and normalization/mapping version. Worker count and invocation limits do not change coverage identity: an unlimited invocation can continue the same incomplete trial. Select the latest incomplete matching pass; otherwise create a new pass, even when the previous pass completed. Keep progress for incompatible scopes separate. Store seen external IDs and history targets in PostgreSQL and iterate targets in bounded batches; never build a citywide dictionary or submit all history futures at once. Keep prior diagnostic totals for reporting, but compute completion eligibility from current unresolved work; successfully retried failures must not permanently poison a pass.

Tile response transaction: parse/filter, stage candidates requiring details, determine trial selection for resolved candidates, batch upsert their sites/bins, record seen IDs, recompute affected site means, and write tile status together. Staged candidates retain selected tile coordinates and mapped inputs in PostgreSQL; do not discard missing metadata or assign a fallback site before resolving required details. Fully resolved/covered tiles get complete status. Tiles with pending details or site limits that omitted eligible records remain partial. Persist the trial's selected site keys so matching limited reruns reuse their bounded selection; unlimited continuation removes the selection restriction and revisits omitted records.

Detail response transaction: validate and map the detail response with its staged coordinates, apply resolved eligibility/trial selection, upsert the Site/Bin, record eligible seen membership, recompute affected site means, and save detail progress atomically. A successfully resolved excluded candidate receives an exclusion checkpoint without creating a Bin or marking it eligible/seen. Save the resolved mapped attributes to pass progress for reuse across neighboring tiles and interruption recovery. Complete a tile only after all admitted candidates are resolved; a failed detail request leaves it partial. Fetch at most one successful detail response per external ID per pass, with failures retryable. A new full refresh uses new detail checkpoints and refetches required metadata. Staging keeps each successful response durable without holding a city's candidates in memory.

History response transaction: resolve the bin by external ID, batch upsert usable events, and save page/continuation state. Mark a page complete only if its response and essential events are valid. If valid events commit from a page containing an invalid attempt, keep its checkpoint partial, log the issue, and return failure; reruns reprocess it idempotently. Fetch from the fixed HTTPS history endpoint with `page=N`, using validated `meta.last_page` or equivalent continuation; never follow arbitrary API links. Preserve the supplied upper pagination sanity limit. If last_page, per_page, or total changes incompatibly, invalidate that bin's page checkpoints and re-read from page 1 while retaining rows. Bound restarts to five per invocation; a rerun receives a fresh restart allowance so old errors do not prevent eventual recovery. This addresses detectable changes but cannot guarantee an immutable source snapshot.

Alternative: local checkpoint files or a single transaction for the entire import. Files cannot atomically track database writes; a citywide transaction loses requested progress and delays visibility.

### 5. Bound network work and serialize database writes

Use one ThreadPoolExecutor with default four workers, a bounded in-flight queue, and a main-thread database writer. Workers fetch/decode individual tiles, required bin details, or individual history pages; they never share SQLAlchemy sessions or write site rows. Replenish futures as responses are persisted, avoiding unbounded submission and response buffering. No transaction or row lock should be held during an HTTP request.

Acquire a nonblocking PostgreSQL session advisory lock for this importer on a dedicated connection for the command's lifetime. Reject a second simultaneous importer with a clear nonzero diagnostic. A crash releases the lock automatically. This serializes import passes across processes, preventing one pass's cleanup racing another's inserts; the unique keys remain the durable integrity guarantees. Truck HTTP operations remain independent.

Retries retain the reference's five-attempt bounded exponential backoff (cap around 20 seconds) for temporary transport errors, throttling, and server failures. Permanent client errors and malformed essential data are reported distinctly. Treat 204/empty tile results as successful only under the verified endpoint contract; verify the reference's 404-as-empty assumption before enabling it. Unexpected tile 404, required detail 404, and history 404 remain unfinished failures. Any unresolved aggregate features, including tiles mixing clusters and physical points, cannot establish complete physical-bin coverage; valid physical candidates can still commit. Apply existing per-transaction statement and lock timeouts to manageable database batches.

For a repeated external ID with differing eligible tile observations, retain the lexicographically smallest `(z,x,y)` source tile's mapped values for that pass and record the winner in seen progress. Conflicts within the same tile use the smallest canonical payload as a deterministic tie-break; committed detail metadata remains authoritative. Whichever response finishes first can commit, but a later preferred tile can update the same Bin. Log conflicts; unusable identities or unresolvable data invalidate completion. This yields an order-independent final choice without retaining all bins in memory. Identical observations only refresh seen membership.

Alternative: worker-owned database sessions and per-site locks. Rejected because one writer and one import lock are sufficient for the MVP and avoid site averaging/cleanup races.

### 6. Finalize only complete coverage and scope removal to bin coordinates

An unlimited matching pass advances to finalization only when all required tile coverage, required bin details, every discovered eligible bin's history, and essential validation succeeded. Nonzero `--max-sites` or `--max-tiles` always means incomplete trial, even if the selected requests all succeeded or limits exceeded the available results. Trials exit 2; request/validation/persistence failures exit 1; full success exits 0. Defaults stay aligned with the reference (`--max-sites 10`, `--max-tiles 0`, workers 4, zoom 17, Vilnius bbox).

In one final transaction, identify stored bins within inclusive west/east and south/north bounds that have no eligible seen record in this pass. Delete those bins (cascading their histories), remove sites made empty by those deletions, recalculate remaining affected means, and mark the pass complete. Scope uses each Bin's stored coordinates, never its Site's mean: a site can include distant members outside the current bounds. A returned bin now excluded by waste/group/city filters is absent from the eligible set and follows the same in-bounds removal rule. All out-of-bounds bins and their histories survive.

A verified entirely empty coverage pass is allowed to remove all in-bounds bins. Failures and invalid/aggregate-only coverage must not masquerade as empty data. No global site pruning is needed: only sites affected by membership changes/deletions are candidates. If cleanup fails, its deletions and completed marker roll back together, and resume retries finalization without re-fetching already committed work. After completion, the next manual invocation uses a new pass and re-fetches history beginning with page 1.

Alternative: delete per tile or clear the whole registry before refresh. Rejected because neighboring tiles, partial coverage, or a crash could remove valid records and erase history outside the requested scope.

### 7. Retain configuration and manual execution conventions

Keep `DATABASE_URL`, root dotenv discovery, environment precedence, extra-key tolerance, sanitized configuration errors, engine ownership, and existing Docker/native command forms. Replace old GIS-only `BIN_SYNC_SOURCE_URL` with explicit configurable VASA tile, detail, and history URL templates (proposed `VASA_TILE_URL_TEMPLATE`, `VASA_BIN_URL_TEMPLATE`, and `VASA_HISTORY_URL_TEMPLATE`), validated placeholders and HTTPS endpoints. Retain positive finite `BIN_SYNC_HTTP_TIMEOUT_SECONDS` with documented example 30 seconds. Settings needed by the importer should not introduce source I/O into server/migration startup. Update `.env.example` and Compose forwarding; document how operators update their existing `.env`, without rewriting it.

Document trial and full commands:

```bash
docker compose exec backend uv run python -m app.interfaces.bin_sync --max-sites 10
docker compose exec backend uv run python -m app.interfaces.bin_sync --max-sites 0 --max-tiles 0
```

Native equivalents run from `backend/` with the same module and an accessible exported database connection. No new recurring/background mode or automatic import is added. Add dependencies with uv and keep its lockfile in sync. Update current README/data/truck verification procedures to stop executing obsolete table queries; retain earlier verification results as historical evidence clearly labeled with their old revision.

## Risks / Trade-offs

- [Destructive replacement cannot recover old records] -> Preserve historical migrations, state the data loss before execution, verify on disposable populated storage, and use a database backup if existing records are wanted. Downgrade cannot reconstruct discarded data.
- [Live dependencies were not accessible during exploration] -> Inspect actual foreign keys before migration execution. An unexpected external reference requires clarification, not a broad cascading drop.
- [Tile 404 or cluster-only responses could appear empty] -> Verify representative endpoint semantics and individual-bin coverage before declaring authoritative success; fail incomplete otherwise.
- [Source data can change during a resumed pass] -> Document best-effort traversal and detect pagination inconsistencies. Later completed-pass refresh re-reads all pages, but no transactional provider snapshot is promised.
- [Address grouping can combine physically distant containers] -> Keep individual bin coordinates; label site coordinates as arithmetic averages and do not use them as asserted entrances.
- [Composite history key can merge identical-time/status attempts] -> Document the limitation and validate available API fields. A material change to identity needs an artifact update before implementation proceeds.
- [NUMERIC field name assumes cubic metres] -> Store volume unchanged and document the unverified unit prominently in data documentation and summaries.
- [Final cleanup is a larger transaction] -> Use indexed pass membership and set-based deletion/averaging, measure on the expected city dataset, and retain finite statement/lock timeouts; failure rolls back only finalization and is resumable.
- [Older `truck-ui` deltas could restore obsolete requirements] -> Archive `truck-ui` before `update-data`; this change's collection/truck deltas then supersede the incompatible route-history promises.

## Migration Plan

1. Verify the live schema matches known dependencies and validate representative VASA tile/detail/history payloads with read-only requests before executing a destructive migration. Investigate the specific 404, pagination, timestamp, and zoom assumptions; stop for material conflicts.
2. Implement the new reviewed migration, models, VASA integration, importer, configuration, and docs through apply. Keep `0001` through `0003` unchanged and keep the truck contract intact.
3. Verify fresh and populated upgrades, repeated upgrades, schema/model agreement, and fleet preservation on disposable PostgreSQL storage. The downgrade policy is explicitly unsupported: the new revision's downgrade raises an actionable message explaining that restoring a backup or recreating disposable storage is required; it must not pretend to recover old records.
4. Execute a manual limited import, interrupt/resume it, and promote matching coverage to unlimited import. Verify progress/data atomicity and subsequent fresh refresh/removal. Do not execute operational import during migrations or startup.
5. Deploy through the existing migrate-before-serving path, which will perform the schema transition once but no external import. An operator then launches the trial/full command explicitly. Record destructive schema scope and the manual invocation in documentation.
6. Archive completed `truck-ui` before archiving `update-data`; review the merged collection/truck contracts to ensure obsolete route requirements do not return. Archival remains a separately requested workflow; apply does not archive either change.

## Open Questions

No unresolved product decisions block this plan. The exact provider volume unit remains unknown; preserving the raw value and documenting the assumption is the accepted contract. Live endpoint and dependency checks listed above are implementation verification gates, not permission to change that contract silently.
