wq# Tasks

## 1. Resident-request persistence

- [x] 1.1 Add `ResidentRequest` and bidirectional Bin relationships in `backend/app/infrastructure/models.py`, plus additive revision `0005_create_resident_requests.py` after `0004`, with exactly three required columns, generated BIGINT identity, cascading foreign key, bin index, and the explicit Vilnius-local server default; verify ORM metadata and the upgraded table match with `uv run alembic check` and schema inspection.
- [x] 1.2 Create the migration/storage section of `docs/resident-request-verification.md` with reproducible disposable database setup, clearly synthetic parent/history/truck/import-progress fixtures, and SQL commands using meaningful failure exits; execute populated-`0004` and fresh upgrades, repeated `upgrade head`, and feature-only downgrade/re-upgrade, confirming existing records and identities survive and no import runs.
- [x] 1.3 Extend and run the documented storage checks for timestamp type/default under a UTC session, seasonal Europe/Vilnius conversion, required fields and nonexistent parents, multiple same-bin/same-time records, bin deletion cascade and rollback, and surviving-bin references; verify only `id`, `bin_id`, and `timestamp` are stored, requests survive restart, and other bins' records remain unchanged.

## 2. Public bin APIs

- [x] 2.1 Extend `backend/app/interfaces/bins/schemas.py`, `router.py`, and `app/services/bins.py` with `GET /bins/{bin_id}` using the existing read-only session; verify curl/OpenAPI returns exactly `id`, `address`, `inventory_number`, `waste_type`, `latitude`, and `longitude`, retains JSON nulls, uses internal IDs, and returns the specified 404/422 responses including BIGINT overflow.
- [x] 2.2 Add `app/interfaces/resident_request_session.py`, `app/services/resident_requests.py`, and the nested POST route with a short parent key-share lock, bounded waits, server-provided timestamp, commit-before-success, and generic rollback/error handling; verify a bodyless POST returns `201 {"success": true}` and SQL shows one new row for the correct parent at Vilnius local time.
- [x] 2.3 Extend `docs/resident-request-verification.md` and the README with both endpoint contracts and executable API/SQL checks; run missing/invalid/deleted-parent, repeated independent POST, forced database-failure, and concurrent parent-deletion checks on disposable storage, confirming errors contain no database details, failed transactions leave no partial rows, successful rows survive restart, and service history is unchanged.

## 3. Standalone resident page

- [x] 3.1 Add the resident page/API modules and register `/resident-request/:bin_id` outside the admin route with a local existing toast provider; verify a direct URL and browser refresh load the bin via `/api/bins/...` without role selection, admin navbar, or admin layout, and preserve string route IDs without numeric rounding.
- [x] 3.2 Implement Lithuanian bin identification, `N/A` formatting, existing waste labels, loading/not-found/load-error states, read retry, pending submission guard, submission error toast/retry, and stale-response protection for both reads and writes; verify invalid/missing IDs hide the form, delayed rapid-click submission sends one POST, failure uses the exact supplied toast, retry remains usable, and switching bin URLs cannot show the previous bin's result.
- [x] 3.3 Implement the single-column phone layout, bottom-positioned full-width 48px-or-taller button with safe-area spacing, visible keyboard focus and state announcements, and success confirmation with a green checkmark, specified text, and supplied responsive GIF; verify 320px and larger viewports, long/null values, keyboard use, GIF failure, absence of a success-state submit button, and reload permitting a fresh submission without automatically creating a row.
- [x] 3.4 Add the page walkthrough and browser failure/recovery checks to `docs/resident-request-verification.md` and document the public URL, minimal stored fields, local naive timestamp convention, cascade lifecycle, and feature exclusions in the README; execute the documented walkthrough and confirm it uses the exact Lithuanian copy and GIF URL from the spec.

## 4. End-to-end integration checks

- [x] 4.1 Run the complete flow against the real frontend/API and disposable migrated PostgreSQL storage: open a bin URL, identify it, submit once, see success, and read the committed row; repeat with submission failure/retry, backend restart, and parent cascade deletion, recording evidence in the existing verification document and confirming bin/history reads, admin browsing, and truck management remain usable.
- [x] 4.2 Run `npm run build` and `npm run lint` from `frontend/`, the documented migration consistency checks, and `openspec validate resident-reqs --strict`; resolve change-related failures and verify the final diff stays within this slice, with no additional analytical pipeline, duplicate protection, or metadata fields.

## 5. Resident page presentation revision

- [x] 5.1 Extend the public bin lookup with linked-site address and physical-bin coordinates; verify the expanded response/OpenAPI contract and existing missing/invalid-ID behaviour.
- [x] 5.2 Place a compact noninteractive map beneath the title and address before the existing fields; replace all ready content on success with a centred large green circle, white checkmark, exact `Jau vykstame pas Jus` text, and the supplied GIF; verify mobile layouts, fixed map interactions, submission recovery, and media/map failures.
- [x] 5.3 Update the README and repeatable verification walkthrough for the revised screen, run build/lint and strict OpenSpec validation, and record verification evidence.

## 6. Latest service information card

- [x] 6.1 Extend the public bin response with the latest history entry’s naive date and service status, or null; add a light-blue Info card between the fields and button, omit it without history, preserve local time and label failed visits as attempts; verify selection/serialization/rendering with lightweight in-memory checks and document manual UI checks without launching a browser or full build.

- [x] 6.2 Centre the service card in the space between fields and button, soften its background with translucent light blue, display only the stored calendar date, and use exactly `Paskutinis aptarnavimas atliktas`; update the artifacts and verify rendering with lightweight checks.

- [x] 6.3 Darken the information card icon and border slightly and make the label and date black, preserving readable contrast and the existing translucent appearance.
