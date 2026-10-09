# Proposal

## Why

Truck capacity currently counts collection sites per trip, which cannot express the waste volume a vehicle can carry. Updating the existing Truck slice to use cubic metres and record the operating company gives administrators meaningful fleet data and establishes the capacity contract for future routing. The landfill extension records an explicitly selected receiving facility using the supplied GeoJSON catalog.

## What Changes

- **BREAKING** Replace `max_bins_per_trip` with required positive numeric `max_volume_m3` throughout Truck storage, API requests/responses, filters, statistics and the existing `/admin/trucks` screen. Accept fractional volumes and remove the old 1–99 limit.
- Add required `waste_carrier` as a normal text column. Use a select with `Kauno švara`, `Biomotorai`, `Ecoservice` and `Ekonovus` in the current create/edit UI and add a matching carrier filter. Do not constrain possible carrier names in the database.
- **BREAKING** Truck responses contain exactly `id`, `name`, `max_volume_m3`, `waste_carrier`, `landfill_id` and `available`; keep `deleted` internal and noneditable.
- Add a migration after revision `0004`. The user confirmed that there are no existing trucks, so no conversion or backfill is needed. Guard this assumption by refusing an unexpectedly populated legacy truck table with an actionable diagnostic, preserving its records and schema.
- Add `landfills`, seeded with all three records from `vilnius_waste_facilities.geojson`, generated integer IDs starting at 1, separate latitude/longitude, source IDs and every property plus collection metadata, excluding GeoJSON `type` fields. Preserve source values as supplied; they are not independently verified operational facts.
- Add migration `0006` after the implemented volume revision `0005`, and a nullable `trucks.landfill_id` foreign key for existing unassigned trucks. Require an explicit valid selection for create and edits of unassigned trucks; never assign a default destination. Add read-only `GET /landfills` and a named-facility dropdown in the existing modal.
- Follow-up revision `0007` makes every landfill field except generated `id` and dropdown `name` nullable, retaining seeded values, source-ID uniqueness and coordinate checks. API/frontend catalog types accept missing details as null.
- Reuse existing list/modal/filter components and keep Lithuanian text, availability icons, pagination, mutation feedback and soft deletion. Display capacity with `m³` and change the existing fleet-average card to average maximum volume.
- Update current documentation and repeatable manual verification instructions. Route optimization, volume prediction, discovery, authentication, driver UI landfill management screens, automatic destination discovery and Truck fields beyond the requested landfill reference remain outside this change.

## Capabilities

### New Capabilities

None; extend the existing vertical slice.

### Modified Capabilities

- `truck-management`: Volume-based read/write contracts, validation, volume and carrier filters, carrier selection, updated list/modal, whole-fleet volume statistics and required landfill selection with a read-only catalog.
- `collection-records`: Truck volume/carrier persistence and a guarded volume schema transition, seeded landfill records and Truck references that preserve existing collection data.

## Impact

- Backend: `backend/app/infrastructure/models.py`, `backend/app/interfaces/trucks/{schemas,router}.py`, `backend/app/services/trucks.py`, landfill lookup HTTP/service modules and Alembic revisions `0005`/`0006`/`0007`. Retain the existing transaction and startup migration paths.
- Frontend: existing files under `frontend/src/pages/trucks/`; reuse the current select, dialog, input and pagination components without adding dependencies or screens.
- Shared contracts: create/patch bodies, truck representations, `min_max_volume_m3` / `max_max_volume_m3` / `waste_carrier` list parameters `average_max_volume_m3` statistics, `landfill_id` and the landfill lookup response. Frontend and backend must move together; no compatibility alias can convert site counts into volume.
- Current README and verification procedures must replace obsolete capacity examples; historical migrations and archived change artifacts remain historical evidence.
- Planning default: carrier mutation values are trimmed nonempty strings at the API, while only the frontend restricts selection to the four current options. This keeps future names storable and readable without a schema migration.
- Material limitation: the empty-fleet fact comes from the user; local API and Docker access were unavailable during exploration. Runtime migration/API/UI checks remain implementation work. Existing Bin volume units remain an independent unverified assumption; this change does not establish their suitability for route optimization.

- Confirmed landfill policy: selection is required for create/edit; existing trucks remain unassigned until explicitly edited. Assigned partial PATCH preserves an omitted landfill; a nonempty edit of an unassigned truck requires its landfill. Empty PATCH remains a read of unchanged values.
