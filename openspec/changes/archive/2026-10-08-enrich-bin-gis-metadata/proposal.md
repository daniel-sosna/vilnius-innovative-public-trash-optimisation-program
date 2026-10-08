# Proposal

## Why

The collection-site registry needs to retain site type and greening information available from the public GIS layer. Importing this registry should be an explicit setup operation: automatic GIS requests on startup, development reload, and a daily timer add unnecessary coupling and delay request serving.

## What Changes

- Extend Bin with nullable, unrestricted text fields `type` and `greening`, using a new additive migration that preserves existing collection records.
- Request all attributes using the supplied layer 29 GeoJSON URL, retain its 50-record pagination and spatial relation, and retrieve every page before publishing updates.
- Map all ten supplied `TIPAS` codes to their Lithuanian labels and `ZELDINIMAS` codes 1/2/3 to `Taip`, `Ne`, and `Taip, agentūrai ES pritarus`.
- Store missing metadata as `NULL`. As explicitly agreed, unknown codes become `NULL` with a warning, and an otherwise valid site remains importable. Mapping tables do not restrict the database's accepted text values.
- Include both metadata fields in the existing atomic Bin upserts, preserving IDs, absent sites, and operational history.
- **BREAKING:** Remove startup and periodic Bin imports. Keep migrations in the existing startup entrypoint; populate Bins only when an operator explicitly invokes the existing import command. Each invocation imports the complete registry once and exits; deliberate reruns remain supported.
- Remove the synchronization timer, stop event, and import-related shutdown wait, together with `BIN_SYNC_INTERVAL_SECONDS` in settings, Compose, example configuration, and current operator instructions.
- Require the remaining source URL and HTTP timeout from the root `.env` or environment rather than Python/Compose fallback values. Document creating `.env` from `.env.example`, use the supplied full query URL, and keep environment overrides available. Native commands load the root `.env` independently of their working directory.
- Move the GIS client and feature mapping to `app/integrations/vilnius_gis.py`; retain database and ORM persistence in `app/infrastructure/` and the reusable upsert workflow in `app/services/`.
- Update operator documentation and repeatable manual verification procedures. This change adds no frontend, prediction, route generation, or metadata-editing API.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `collection-records`: Expand the exact Bin field contract to six columns and permit nullable, unrestricted type and greening text without modifying required entity relationships. Prepare schema before serving without implying an automatic Bin import.
- `bin-synchronization`: Retrieve richer source attributes, map optional metadata with nonfatal unknown-code diagnostics, and upsert those fields only on explicit command invocation. Replace automatic lifecycle requirements with manual-only importing and obtain the remaining configuration from dotenv/environment inputs.

## Impact

Affected implementation includes `backend/app/infrastructure/models.py`, additive revision `0002`, moving `backend/app/infrastructure/vilnius_gis.py` to `backend/app/integrations/vilnius_gis.py`, `backend/app/services/bin_sync.py`, `backend/app/interfaces/bin_sync.py`, `backend/app/main.py`, `backend/app/core/config.py`, `docker-compose.yml`, `.env.example`, README, and manual verification documentation. The importer and Alembic retain the shared Settings class; FastAPI no longer owns an import lifecycle. No new dependency or deployment service is expected: pydantic-settings and its dotenv support already exist.

The current main specs explicitly limit Bin to four fields, synchronization updates to address/coordinates, and require automatic startup/periodic synchronization; this change deliberately updates those contracts. Schema preparation remains automatic in the documented startup path, but an empty registry stays empty until a successful operator import. Startup, restart, reload, and idle application runtime make no GIS requests. GIS remains authoritative for the two new fields, so a later explicit import can overwrite manually entered metadata. Unlisted attributes returned by `outFields=*` are not persisted.

Exploration on 8 October 2026 observed 1,351 sites, including 178 null `TIPAS` values and 740 null `ZELDINIMAS` values. The initial five type examples occur in the current snapshot, while the supplied ten-code mapping matches the layer's complete domain. Counts are observations, not acceptance constants. Stable external identity and existing pagination semantics remain assumptions; future unknown codes are handled by the confirmed policy rather than inferred labels.

Source: [Vilnius GIS layer metadata](https://opencity.idvilnius.lt/gis/rest/services/Miesto_tvark/Miesto_tvarkymas_public/MapServer/29?f=pjson).
