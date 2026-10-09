# Proposal

## Why

The current registry models GIS collection sites as bins and requires route-linked emptying observations, so it cannot represent VASA physical containers or their historical service attempts. Replace that foundation with address-grouped sites and physical bins, and adapt the supplied VASA exporter into a manually invoked PostgreSQL importer that can recover from interruptions.

## What Changes

- **BREAKING**: Destructively replace old `bins` and remove the actual plural tables `routes`, `route_stops`, and `service_events`; their records are intentionally not migrated. Preserve `trucks`, its existing records, API, UI, retirement behavior, and capacity meaning of sites per trip.
- Introduce `sites`, physical `bins`, and `bin_hist` with generated BIGINT identities, explicit relationships, source field mappings, and database uniqueness/check constraints.
- Store bin-level `district`, `region`, `sub_district`, `city`, `street`, `house_number`, `postal_code`, and `territory_type` as nullable TEXT. Preserve source postal-code text without padding or borrowing values from client addresses. Remove proposed `last_service_date` and `next_service_date` from bins; do not store the container snapshot's `is_serviced`, `service_date`, `not_serviced_reason`, or `next_service_date` on bins. Actual attempts remain in `bin_hist`.
- Add `sites.site_key TEXT NOT NULL UNIQUE` for normalized address identity while retaining a readable address. Group exclusively by registered address; missing addresses receive isolated keys based on VASA bin identity. Coordinates are means of all current member bins, not surveyed collection points.
- Replace the existing manual GIS import behind `python -m app.interfaces.bin_sync` with the supplied script's VASA tile/history parsing and PostgreSQL ingestion. Import the three specified waste types, exclude `Individualios valdos`, and produce no CSV files.
- Extract the eight bin metadata fields from tile attributes when present; use `/vasa-api/api/v1/dumpsters/{id}` to resolve fields missing from tiles. Persist required detail-response work with resumable progress, bounded concurrency, and the same failure/completion rules as tile/history work. A new completed-pass refresh re-fetches any required details.
- Persist each tile and history page with its checkpoint atomically, using bounded network concurrency, a single database writer, retries, and batch upserts. Incomplete passes resume; invoking the importer after a completed pass starts a fresh refresh.
- After a complete successful pass, delete unseen bins only within its configured bounding box, including their history; delete newly empty sites and recalculate surviving affected sites. Trials, errors, and interrupted passes never perform this removal.
- Document trial/full commands and repeatable manual verification. Add no automated tests, scheduled imports, collection UI, route optimisation, or ML functionality.

## Capabilities

### New Capabilities

None. Reuse the existing collection and import boundaries.

### Modified Capabilities

- `collection-records`: Replace site-as-bin and route/service-event contracts with address-grouped sites, physical bins, raw service attempts, numeric nullable fill observations, and the deliberate destructive transition; retain current truck semantics.
- `bin-synchronization`: Replace GIS retrieval and whole-run atomic publication with explicit VASA import, incremental persistence, resumable passes, completed-pass refresh, and bounded missing-bin removal.
- `truck-management`: Update the soft-delete contract's obsolete route-history scenario to the retained fleet behavior after removal of route records. This capability already exists in the completed but unarchived `truck-ui` change at the same capability path; archive `truck-ui` before archiving `update-data`. No duplicate capability or truck feature is introduced.

## Impact

- Backend: a new Alembic revision after `0003`; `app/infrastructure/models.py`; `app/services/bin_sync.py`; `app/interfaces/bin_sync/`; the replacement VASA integration in `app/integrations/`; shared database/configuration helpers as needed for explicit importer ownership and locking.
- Configuration/docs: replace GIS-specific source settings in `.env.example`, Compose, README, and current verification procedures with VASA tile/detail/history endpoint configuration, keeping `DATABASE_URL`, root dotenv loading, environment precedence, and existing native/Docker commands. Do not rewrite an operator's `.env` automatically.
- Dependencies: add `requests` and `mapbox-vector-tile` to the backend's uv-managed dependencies and lockfile when implementing. The reference is `/home/stitas/Desktop/p/venv/vasa_export_address_only.py`; the runtime must not depend on that external file.
- Spec integration: main collection specs and `truck-ui` currently promise retained route-linked history. This change explicitly supersedes those contracts for removed entities. Preserve historical migrations and completed change artifacts; apply/merge the deltas in `truck-ui` then `update-data` order.
- Assumptions: VASA `volume` is stored unchanged under `capacity_m3`, with cubic metres unverified. History uniqueness uses `(bin_id, date, was_serviced)` and can collapse attempts sharing that timestamp/status; service timestamps remain timezone-naive. Refresh upserts existing events and retains subsequently supplied fill observations.
- Verification: read-only live catalog checks matched the expected dependency graph; representative tile/detail/history requests verified extent/orientation, metadata fallback, naive timestamps, pagination, and valid empty MVT. Initial HTTP 403 was resolved with a standard browser User-Agent. Rootless Podman verified packaged startup/imports when the host Docker socket was inaccessible. Detailed results are in `docs/data-foundation-verification.md`. Volume units and tile-404-as-empty semantics remain unverified: preserve raw volume and treat unexpected 404 as incomplete failure. VASA has no demonstrated snapshot token, so interrupted pagination remains best effort.
