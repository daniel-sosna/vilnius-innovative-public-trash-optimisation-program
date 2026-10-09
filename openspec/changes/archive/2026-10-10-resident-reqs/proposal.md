# Proposal

## Why

Residents currently cannot report that a specific bin needs emptying. A small public, phone-first request flow makes resident observations demonstrable through the real system and stores raw inputs that future prediction work can use.

## What Changes

- Add the standalone public route `/resident-request/{bin_id}`, using internal `Bin.id`, with a fixed location map beneath the title, the linked site address as the first field, existing Lithuanian bin details, and one prominent bottom-positioned `Siųsti` action.
- Show a pale translucent light-blue information card with an information icon centred between the fields and send button, using only the latest bin history entry’s calendar date and the exact label `Paskutinis aptarnavimas atliktas`; hide the card when history is absent.
- Add a minimal bin-read API and an API that resolves the bin, stores a resident request, and confirms success only after persistence commits.
- Add `ResidentRequest` storage and an additive migration for `resident_requests`, containing only generated `id`, required `bin_id`, and required `timestamp`.
- Generate timestamps from Europe/Vilnius local time and store them without timezone information. Cascade request deletion when the parent bin is deleted, including registry cleanup.
- Cover loading, missing-bin, retryable loading/submission errors, pending submission, and success with the centred solid green circle with a white checkmark, `Jau vykstame pas Jus`, and the supplied responsive GIF, replacing all previous page content.
- Keep QR generation/scanning, authentication/accounts, CAPTCHA, rate limiting, identity/IP/device capture, anti-spam and duplicate detection, moderation, admin request management, ML/routing integration, and notifications outside this change.

## Capabilities

### New Capabilities

- `resident-requests`: Public bin identification and resident emptying-request submission, with a simple Lithuanian mobile interface and recoverable states.

### Modified Capabilities

- `collection-records`: Add minimal resident-request records with Vilnius local, timezone-naive submission timestamps, an additive schema upgrade, and parent-bin cascade deletion.

## Impact

- Backend: extend `app/interfaces/bins/` and `app/services/bins.py`; add a focused resident-request write service/session dependency; extend `app/infrastructure/models.py` and add the next Alembic revision after `0004`.
- APIs: add `GET /bins/{bin_id}` and `POST /bins/{bin_id}/resident-requests`; the existing frontend proxy exposes these as `/api/bins/...`. Existing history and admin API contracts remain compatible.
- Frontend: add the public route in `src/App.tsx` and a resident page/API module, reuse the existing LocationMap (noninteractive), Button, toast component, and waste-type translations, and mount a toast provider for the standalone page.
- Storage/import: requests survive metadata refreshes and restarts while their bin exists; deletion relies on a database cascade so the importer's bulk deletion remains compatible.
- Documentation/verification: update the README and add a repeatable manual API, SQL, migration, and phone-layout verification procedure with clearly synthetic fixtures.
- Confirmed assumptions: bin references use internal IDs; all timestamps share the Vilnius local-time convention; request records need not survive parent deletion. The address comes from the bin’s linked Site.address and map coordinates from the physical Bin, not the site average. Requests record resident reports, not verified fill levels or service events; the confirmation text does not initiate dispatch.
- Proposed minor defaults: initial load failures reuse `Kažkas nepavyko. Bandykite dar kartą.` with the existing retry label `Bandyti dar kartą`; success is page-session state, so a reload permits another request.
- Remaining limitations: the supplied GIF is externally hosted and its availability cannot determine submission success; unambiguous absolute ordering during a repeated daylight-saving hour is not preserved by the selected naive timestamp format. No blocking scope uncertainty remains.
