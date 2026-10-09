# Tasks

Groups 1–5 record completed volume/carrier work at revision 0005. Groups 6–9
extend that delivered model and contract with the landfill reference; their
seven-field storage and six-field responses supersede the earlier field counts.

## 1. Truck persistence and guarded migration

- [x] 1.1 Update `backend/app/infrastructure/models.py` to the six-field Truck model with required Numeric volume and Text carrier, replace the old range check with positive finite volume validity, and retain name/identity/retirement invariants; verify ORM metadata contains no old capacity column or carrier-name constraint.
- [x] 1.2 Add the next Alembic revision after `0004` with a transactionally locked empty-table preflight, actionable unexpected-row diagnostic, required volume/carrier columns and an empty-table-only downgrade; verify upgrade/downgrade succeeds with empty trucks and rejects populated tables including retired rows without schema/data changes.
- [x] 1.3 Manually verify fresh upgrade, initialized `0004` storage with existing collection data but no trucks, and repeated `uv run alembic upgrade head` after creating volume-based trucks; run `uv run alembic check`, confirm collection/import records and generated identity remain intact, and confirm a valid unlisted carrier can be stored while invalid volumes cannot.
- [x] 1.4 Update README schema/startup notes and migration sections of `docs/truck-management-verification.md`, including new fixtures, direct-storage checks and rollback restrictions; keep historical migration examples clearly scoped to their revisions, update any current-head insert in `docs/data-foundation-verification.md`, and verify the documented disposable migration procedure matches the new head.

## 2. Truck HTTP contracts, filtering and statistics

- [x] 2.1 Update `backend/app/interfaces/trucks/schemas.py` for the four create/patch inputs and five response fields, retaining partial PATCH/null/extra-field semantics and enforcing actual positive finite JSON numbers plus trimmed nonempty carrier strings; verify create/patch accept 0.5, 18.5 and 120, reject numeric strings/booleans/nulls/blank carriers/obsolete fields, and preserve omitted values.
- [x] 2.2 Update `backend/app/services/trucks.py` projections/serialization, volume bounds, exact carrier matching and fleet average; update the router to `min_max_volume_m3`, `max_max_volume_m3` and `waste_carrier`; verify response numbers across list/detail/create/patch/stats, consistent filtered counts/items, AND/inclusive predicates, and whole-fleet averages independent of filters/pages.
- [x] 2.3 Exercise all six existing truck endpoints against the migrated disposable database: confirm 201/200/204/404 behavior, page size/order and empty PATCH, create/read an unlisted carrier, and delete a truck then inspect retained deleted=true/available=false with unchanged collection data; verify retired trucks disappear from list/detail/statistics and cannot be edited or deleted again.
- [x] 2.4 Update current README API/filter/statistics examples and API sections of `docs/truck-management-verification.md` to the numeric volume/carrier contract; verify the documented curl requests and expected values, invalid bounds including nonfinite/inverted ranges, empty-fleet statistics and unknown-field errors against the running backend without adding automated test files.

## 3. Existing Truck screen, modal and filters

- [x] 3.1 Update `frontend/src/pages/trucks/api.ts` Truck/TruckStats types, field-error mapping and shared four-carrier options; add positive finite decimal parsing/validation for comma/point input and volume formatting, removing site-count validation; verify blank/zero/negative/nonfinite values are rejected and fractional input sends JSON numbers, with `npm run build` passing after dependent component updates.
- [x] 3.2 Extend `truck-editor.tsx` with volume plus visible `m³` and the required carrier Select, Lithuanian labels/errors, blank create carrier and existing availability default; verify create/edit round trips for each company and fractional volume, correct preloading/reset/cancel behavior, and no request for invalid input or missing carrier.
- [x] 3.3 Update `trucks-page.tsx` rows and query state for volume bounds and carrier filtering, including hasFilters, clear/reset and pagination identity; verify name/volume/carrier/status/delete display, fractional `18,5 m³` formatting, exact combined filters, page-1 resets and last-page recovery after a mutation.
- [x] 3.4 Update `truck-overview.tsx` to `average_max_volume_m3`, `Vidutinė maksimali talpa` and Lithuanian one-decimal `m³` display; verify the empty `—` state, arithmetic average, filter independence and refresh after successful create/edit/delete.
- [x] 3.5 Verify current four-value select restrictions and faithful display of an unlisted carrier inserted through the API: no automatic replacement on open/cancel, explicit listed selection required for modal save; check desktop/320-pixel wrapping, green-check/red-cross indicators, labeled controls and keyboard/focus behavior, then run `npm run build` and `npm run lint`.
- [x] 3.6 Update README Truck UI wording and browser sections of `docs/truck-management-verification.md` for volume/carrier inputs, filters, overview and responsive rows; verify each documented screen action against the running UI, including successful-save toasts and failed-save input preservation, and remove current UI references to site-count capacity.

## 4. End-to-end acceptance

- [x] 4.1 Run the revised vertical-slice procedure through the real frontend proxy and persistent backend: create/edit/filter/page/retire trucks, refresh/restart to confirm persistence, check stale-response cancellation and independent list/statistics retry after a committed mutation, and confirm no external import/optimizer activity; record actual outcomes and any remaining environment limitations in the verification document.
- [x] 4.2 Review the final diff for the requested scope, obsolete capacity references in active Truck code/current docs, and absence of carrier database restrictions or additional Truck fields; verify historical migrations/archives and collection semantics remain intact and `openspec validate truck-update --strict` passes before presenting implementation for review.

## 5. Numeric input follow-up

- [x] 5.1 Restrict editor and minimum/maximum volume input to numeric text while typing or pasting, preserving decimal comma/point, numeric notation, clearing and positive finite validation; manually verify all three controls and numeric request values, then run frontend build/lint and strict OpenSpec validation.

## 6. Landfill storage and migration

- [x] 6.1 Add the Landfill model and nullable Truck FK using the approved source mapping; verify generated INTEGER identity, separate coordinates, all 18 catalog columns, source IDs/metadata and no type/carrier restrictions.
- [x] 6.2 Add self-contained revision `0006` to create/seed all three facilities and add the FK; manually verify exact source values, IDs 1–3/next 4, fresh and populated-0005 upgrade, repeated startup, assignment/referenced-delete constraints, guarded active/retired rollback, collection/import preservation and Alembic model agreement.
- [x] 6.3 Document the catalog provenance, seven-field Truck schema, upgrade/rollback policy and reproducible disposable migration/storage checks in README and verification docs; verify the documented procedure against migrated storage.

## 7. Landfill lookup and Truck HTTP contracts

- [x] 7.1 Add read-only `GET /landfills` with complete ordered catalog responses; verify all source strings/arrays/dates/coordinates and absent-property nulls, with no management writes or network/source-file dependency.
- [x] 7.2 Extend Truck schemas/services/representations with landfill_id and strict existing-ID validation; verify required create, assigned partial PATCH preservation, unassigned edit assignment requirement, empty PATCH, invalid/missing/null/string/bool/fraction IDs, retired exclusion and atomic soft deletion retaining assignment.
- [x] 7.3 Update current API documentation and fixtures to landfill lookup/assignment contracts; run the documented requests and confirm numeric six-field responses, 422 field detail and unchanged filters/statistics.

## 8. Existing Truck modal landfill selection

- [x] 8.1 Add lookup/types/error handling and a required named-facility Select to the existing editor; verify blank create/unassigned state, assigned preloading, numeric payloads, all three options, loading/error/empty save prevention, cancellation and retry preserving values.
- [x] 8.2 Verify real create/edit/retire with landfill selection, keyboard/focus behavior and long option names at desktop/320px; retain numeric-only decimal inputs, carrier selection, filters/statistics and pending-submit behavior, then run frontend build/lint.
- [x] 8.3 Document and exercise current modal selection/loading/error/retry behavior, including existing unassigned trucks and named selection persistence, in the manual browser verification instructions.

## 9. Landfill end-to-end acceptance

- [x] 9.1 Verify fresh startup/restart through the real frontend proxy and backend, persisted assignments, retained retired references and collection snapshots; review final scope/source completeness, record actual outcomes/environment limits, run schema agreement and strict OpenSpec validation.

## 10. Nullable landfill details follow-up

- [x] 10.1 Make all landfill details except ID/name nullable in ORM/API/frontend contracts and add revision 0007 for existing databases, preserving seeded values, source-ID uniqueness, coordinate checks and Truck references; provide guarded downgrade without fabricated values.
- [x] 10.2 Verify fresh and populated-0006 upgrades, name-only storage, null lookup serialization and valid Truck assignment, required ID/name and coordinate/source constraints, guarded downgrade and schema agreement in disposable PostgreSQL.
- [x] 10.3 Update current schema/migration documentation with repeatable nullable-field checks, record actual verification, and run frontend build/lint, focused backend lint and strict OpenSpec validation.
