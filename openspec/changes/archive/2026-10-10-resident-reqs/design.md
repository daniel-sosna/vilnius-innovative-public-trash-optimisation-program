# Design

## Context

See `proposal.md` for motivation and the two delta specs for the behaviour contract. This change spans persistence, HTTP, and the public frontend, so a design artifact is warranted.

Current integration points:

- `frontend/src/App.tsx` has standalone root/fallback routes and nested `/admin` routes. `AdminLayout` owns the existing `ToastProvider`.
- `frontend/vite.config.ts` proxies `/api` to the backend with the prefix removed, including in preview.
- `app/interfaces/bins/router.py` currently exposes only history. Its `CollectionSession` dependency starts a read-only repeatable-read transaction and rolls it back when finished.
- `app/infrastructure/models.py` defines independently generated BIGINT bin identities, nullable inventory numbers, required stored waste types, and naive service-history dates. The database engine configures sessions to UTC.
- Revision `0004` is the current collection schema. `backend/start.sh` runs Alembic before serving. The importer deletes missing bins with bulk SQL, and bin history relies on a database cascade.
- Existing formatting maps all three supported source waste types to Lithuanian and renders missing values as `N/A`.

## Goals / Non-Goals

**Goals:**

- Integrate the new write into the existing backend deployment, database, and `/bins` interface.
- Preserve the selected naive local-time contract independently of database/session/host timezone defaults.
- Keep a saved request and its parent reference transactionally consistent, including around importer deletion.
- Reuse existing UI primitives while keeping the resident page independent of admin layout.

**Non-Goals:**

- Refactoring shared session infrastructure, existing admin pages, the importer, or historical timestamp storage.
- Introducing new services, a request-list/read-management API, persisted aggregate counters, or an analytical pipeline. Broader product exclusions are listed in the proposal.

## Decisions

### 1. Keep a three-column child record and database cascade

Add `ResidentRequest` to `app/infrastructure/models.py` and an additive revision `0005_create_resident_requests.py` after `0004` with:

| Column | Storage contract |
| --- | --- |
| `id` | BIGINT generated always as identity, primary key |
| `bin_id` | BIGINT NOT NULL, foreign key to `bins.id` ON DELETE CASCADE |
| `timestamp` | TIMESTAMP WITHOUT TIME ZONE NOT NULL, server default generating Vilnius local time |

Add an ordinary `bin_id` index for parent deletion and bin-based retrieval. Add bidirectional Bin/request relationships, using database-backed passive deletion consistent with the existing history relationship. Do not add a uniqueness constraint on bin or timestamp: independent reports, including same-time reports, are valid.

Database cascading supports the importer's bulk SQL deletion without changing its cleanup workflow. A restrictive foreign key would block existing cleanup; application-only cascading would miss bulk deletes. Keeping removed-bin reports would require a different identity/retention contract and conflicts with the confirmed cascade decision.

### 2. Generate local time explicitly on the database server

Use a server default equivalent to `statement_timestamp() AT TIME ZONE 'Europe/Vilnius'` in both the migration and ORM metadata. The insert supplies `bin_id`; the database supplies the identity and local submission time. This produces the required naive timestamp even when the database session remains UTC, and follows the timezone's seasonal clock changes.

An unqualified current-timestamp default cast to a naive column would use the session's UTC setting. Host-local `datetime.now()` would depend on deployment defaults. Python `ZoneInfo` could produce the correct value, but the explicit database default avoids separate timestamp logic and makes all inserts use the same clock without an additional Python timezone dependency. Existing history dates and the global connection timezone stay as they are.

The timestamp records local wall time at the insert statement. The user-confirmed assumption is that service history and resident reports share the Vilnius local-time convention; verifying or integrating a requests-since-service feature belongs to future work.

### 3. Extend the existing bins interface with focused services

| Backend route | Request | Success | Errors |
| --- | --- | --- | --- |
| `GET /bins/{bin_id}` | Internal ID in path | 200 with exactly `id`, `address`, `inventory_number`, `waste_type`, `latitude`, `longitude`, nullable `latest_service` | 404 missing/out-of-range positive ID; 422 nonpositive/noninteger ID; generic 500 database failure |
| `POST /bins/{bin_id}/resident-requests` | Internal ID in path; no body required | 201 with `{"success": true}` after commit | Same ID rules; generic 500 database failure |

Add the minimal read schema to `app/interfaces/bins/schemas.py` and a bin-read function to `app/services/bins.py`. GET uses `CollectionSession`, joining the linked Site for its registered `address` and returning the Bin’s own latitude/longitude. No address or coordinate columns are added; site-average coordinates are not used. Return `latest_service` as `{date, was_serviced}` from the bin’s most recent history row ordered by `date DESC, id DESC`, or null if none exists. Read it in the same repeatable-read snapshot, without filtering unsuccessful attempts or loading full history. Follow the existing history service's BIGINT overflow guard before querying.

Add `app/services/resident_requests.py` and a focused `app/interfaces/resident_request_session.py` write dependency, wired into the bins router. Use the existing session factory and the truck write flow as the local pattern, with rollback/error handling covering session creation, operation, and commit errors. Catch database failures without exposing SQL or credentials. Keep read-only collection snapshots intact rather than broadening them into writable sessions or importing a truck-specific dependency.

For POST, resolve the parent with a short `FOR KEY SHARE` lock held through insert and commit. An already deleted parent produces 404; a concurrently attempted parent deletion waits until the short submission transaction completes. The foreign key remains the final integrity guarantee. Use bounded transaction-local statement/lock waits consistent with existing collection requests; timeout failures become ordinary failed submissions. Flush and commit the request before returning success. Never automatically retry a POST in the service or frontend.

A separate `/resident-requests` collection endpoint with a body containing `bin_id` is possible, but the nested route expresses the existing parent and avoids competing path/body identities. Both new endpoints reuse the existing backend router registration and `/api` proxy.

### 4. Mount a standalone page and local toast provider

Add `frontend/src/pages/resident-request/resident-request-page.tsx` and `api.ts`. Register `/resident-request/:bin_id` outside `/admin`, wrapped in its own existing `ToastProvider`. The admin provider can remain where it is; moving all providers or adding an admin link is unnecessary for this slice.

Fetch via `/api/bins/{bin_id}` and submit via `/api/bins/{bin_id}/resident-requests`. Keep the route ID as a string for path construction; validate its positive integer shape and map invalid IDs/GET 422 to the dedicated not-found view. Avoid converting the route ID through JavaScript numeric arithmetic. Abort or disregard obsolete GET requests and reset local state when the bin changes. Guard POST results by the originating bin/page instance so late completion cannot mark another bin successful.

Use explicit page states:

```text
loading --> ready --> submitting --> success
   |          ^           |
   |          +-----------+ submission error + toast
   |
   +--> not-found
   |
   +--> load-error --> loading (retry GET)
```

Only `ready` permits submission. Set a synchronous pending guard as well as disabling the button to suppress repeated events before React renders. Reset it after failure; remove the action after success. Initial load failures use the supplied generic error sentence and existing `Bandyti dar kartą` label. While pending, retain `Siųsti` with a spinner/disabled state to avoid introducing unapproved copy. Success is in-memory page state; there is no local-storage flag or duplicate-detection mechanism.

Reuse `formatValue` and the existing known waste-type translations from `pages/sites/format.ts` without moving unrelated code. No expected imported category needs new wording; if a new category requires translation, obtain wording rather than fabricating it.

### 5. Use a simple phone-first layout

Use one `main` column, roughly `max-w-md`, with horizontal padding, a modest title, and a compact fixed location map immediately beneath the title and a plain definition list ordered `Adresas`, `Konteinerio numeris`, `Atliekų tipas`. Reuse `LocationMap` with `interactive={false}` to disable dragging, touch gestures, wheel/double-click/keyboard zoom, and navigation controls. An optional canvas height class allows a compact resident map while retaining the existing admin map dimensions. Map failure keeps the address, bin details, and submission usable. Between the definition list and action, conditionally render a pale translucent light-blue information card with a slightly darker blue border and decorative Info icon, black label/date text, and a semantic time element. Keep the card background pale in dark mode so the black text remains readable. Centre it vertically in a growing flex area with equal minimum padding above and below; keep the button at the bottom. Use the exact user-selected label `Paskutinis aptarnavimas atliktas` for the latest entry regardless of status. Display only the ISO calendar-date portion of the stored naive timestamp, without interpreting it as a JavaScript Date or converting device timezones. No history means no card or placeholder. Use a `min-h-dvh` flex layout so the full-width, 48px-or-taller button sits near the bottom while content can still scroll on short viewports. Add bottom safe-area spacing; do not overlay a fixed button on content. Apply the existing theme tokens and shadcn Button. Long inventory/waste text wraps at 320px, and larger screens centre the narrow column.

After a committed submission, replace the whole page content, including title, map, fields, and button, with a centred accessible confirmation: a large solid green circle containing a white checkmark, `Jau vykstame pas Jus` underneath, and the exact GIF URL in the spec beneath the text. This is presentation only; it creates no dispatch or route. Bound the image to the column width with proportional sizing. Treat it as decorative with empty alt text because the adjacent text carries the confirmation, and avoid a broken-image placeholder if loading fails. No new animations beyond the requested GIF are needed. Pending and success feedback must be announced; existing toast accessibility is reused.

## Risks / Trade-offs

- Naive local time cannot distinguish the repeated autumn clock hour -> retain the user-selected format; generated IDs can distinguish records, and no absolute-time aggregation is introduced here.
- The response can be lost after a successful commit -> show the requested error/retry behaviour without automatic retries; another explicit submission may create another row under the deliberately non-deduplicating contract.
- A bin can disappear after it was displayed -> resolve it again transactionally at POST time; a failure gets the same retryable submission toast, with no detached record.
- External GIF availability may vary -> the text and checkmark determine success and remain visible when media fails.
- Cascade deletion intentionally removes removed-bin reports -> document this lifecycle alongside history deletion; no separate retention mechanism is introduced.

## Migration Plan

1. Add only the new table, foreign key, default, and index in revision `0005`; do not alter the historical replacement migration.
2. Before activation, verify upgrade from a populated `0004` database and fresh setup, repeated `upgrade head`, and `alembic check` using disposable synthetic storage. Compare existing records and references before/after, check the timestamp column/default with a UTC session, and exercise deletion/rollback there.
3. Apply through the existing startup migration path when activating the implementation, retaining existing PostgreSQL storage. Startup performs no import or refresh cleanup.
4. For feature rollback, stop serving the new route and endpoints and downgrade only `0005` to `0004`. That downgrade drops resident-request storage and loses its records; export those records first if needed. It must leave the existing collection schema intact and must not attempt to downgrade the destructive `0004` transition.
5. Record manual API/SQL and mobile verification in `docs/resident-request-verification.md`, update the README, and run the existing frontend build/lint checks. Use synthetic fixtures for writes, forced database failures, and deletion checks; production/request-management tooling is not part of verification.
