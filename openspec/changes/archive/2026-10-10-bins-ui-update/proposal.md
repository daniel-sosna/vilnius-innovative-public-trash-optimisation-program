# Proposal

## Why

Administrators can browse the collection registry but cannot add a collection site, add a container, or remove obsolete records. Extend the existing Šiukšlių surinkimo vietos screens so the registry can be maintained manually after the completed one-time import.

## What Changes

- Align Site/Bin row delete actions with the shared Truck row delete control, place Site creation beside search, and show only street/house number in Site list rows.
- Add a scrollable create-Site modal at `/admin/sites`, containing address fields, a click-to-select MapLibre map, and one or more removable Bin forms. Persist the Site and all initial Bins atomically.
- Add a Bin creation modal above the list at `/admin/sites/{id}`. Inherit coordinates and address metadata on the backend.
- Require street, sub-district and house number; allow a NULL postal code. Require all five Bin inputs in forms and create APIs, including a positive finite numeric capacity with decimals and no fixed upper bound.
- Offer the four specified waste carriers and three existing waste types in dropdowns. Keep existing database columns nullable/unrestricted where they already are; form/API validation does not add database constraints.
- Generate manual Site keys automatically, populate the specified Vilnius metadata, and give manual Bins NULL external IDs without fabricated history or client counts.
- Add confirmed hard deletion to Site and Bin rows. Deleting the final Bin also deletes its Site; all deletions cascade to history and existing resident requests. Refresh lists and affected statistics without a full page reload.
- **BREAKING**: change Site deletion from RESTRICT to CASCADE and allow NULL Bin external IDs while retaining uniqueness for non-NULL IDs. Introduce a data-preserving migration only for these changes.
- Preserve existing browsing, details, history, Lithuanian text, NULL-to-`N/A` presentation and responsive admin styling. New editable fields use ordinary empty inputs.
- Limit synchronization changes to excluding manual Bins from cleanup. No import rerun, source requests, scheduling, suppression records, or import redesign is part of this work; locally deleted imported records may reappear after a future explicit import.

## Capabilities

### New Capabilities

- `collection-site-management`: manual Site/Bin creation, input validation, address inheritance, location selection, confirmed transactional hard deletion and UI refresh behavior.

### Modified Capabilities

- `collection-records`: manual identities and coordinates, nullable external IDs, preserved optional source attributes, cascading Site deletion and a data-preserving schema upgrade.
- `collection-site-browsing`: preserve read-only GET behavior alongside explicit management actions and distinguish selected manual locations from imported derived locations.
- `bin-synchronization`: exclude NULL-external-ID Bins from bounded cleanup, preserving their Sites when they remain attached.

## Impact

- Backend: `app/infrastructure/models.py`, an Alembic revision after `0005`, Site/Bin routers and schemas, their services, and a writable collection-session dependency. Existing read-only browsing sessions remain unchanged.
- Frontend: existing Site list/details/Bin list, Site API helpers and overview refresh, MapLibre location component, and dialogs following the Trucks patterns. No new dependencies or services are expected.
- API: add `POST /sites`, `POST /sites/{site_id}/bins`, `DELETE /sites/{site_id}` and `DELETE /bins/{bin_id}`. Existing GET payloads and pagination contracts remain compatible.
- Shared contracts: manual records coexist with imported records; resident-request cascades remain effective. API/client consumers must handle the final-Bin Site deletion outcome.
- Proposed defaults: `manual:<UUID>` Site keys; address display `street house_number, sub_district[, postal_code]`; inherit all four address fields from the lowest-ID child, preserving NULLs. Manual creation produces a distinct Site even at an existing address; it does not merge registries.
- Existing Site coordinates remain fixed during admin additions/deletions, consistent with the exclusion of moving existing markers. Imported averaging remains an import behavior. Legacy zero-Bin Sites remain browsable and can accept new Bins with unavailable inherited address fields left NULL.
- Material uncertainties have been resolved through exploration. Remaining verification concerns are transactional rollback/final-child concurrency and map behavior inside a responsive modal; the design and tasks cover them.
- Out of scope: editing existing Site/Bin data, moving existing markers, geocoding/reverse geocoding, route generation, prediction and driver navigation.
