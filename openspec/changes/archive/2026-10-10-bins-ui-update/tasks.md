# Tasks

## 1. Prepare compatible collection storage

- [x] 1.1 Add the next Alembic revision after current head (`0005` at planning time) and update SQLAlchemy for nullable `Bin.external_id` and Site-to-Bin CASCADE, retaining all other optional-column nullability and existing uniqueness/cascades. Verify on disposable PostgreSQL with `alembic upgrade head`, `alembic check`, before/after record comparisons, duplicate known-ID rejection and multiple NULL-ID acceptance.
- [x] 1.2 Implement the downgrade preflight for NULL external IDs and compatible restoration of RESTRICT/NOT NULL. Verify an incompatible downgrade leaves records/schema intact and a compatible downgrade/upgrade succeeds on disposable storage.
- [x] 1.3 Add `external_id IS NOT NULL` to both importer-finalization selection paths only. Verify disposable local SQL candidates exclude manual Bins and manual-only Sites while retaining eligible unseen imported Bins; invoke no VASA import.
- [x] 1.4 Start `docs/collection-site-management-verification.md` with repeatable migration, schema comparison, downgrade and local cleanup-predicate commands; update README's nullable external-ID/deletion contract. Verify the documented commands against disposable storage and record actual results, with no reset/import of the existing registry.

## 2. Deliver Site creation with initial Bins

- [x] 2.1 Add reusable strict Bin-create and Site-create schemas, dropdown value mappings and writable collection sessions while preserving GET sessions. Verify request parsing rejects blanks, NULL required inputs, extra assigned fields, zero-Bin bodies and invalid/nonfinite coordinates or capacity, and accepts optional postal code and positive decimal numeric capacity without adding DB constraints.
- [x] 2.2 Implement server-owned metadata, `manual:<UUID>` keys, address formatting and atomic `POST /sites` with 201 SiteSummary after commit. Verify a two-Bin request through the API plus SQL, including copied coordinates/address, NULL identities/territory/client counts, fixed Vilnius fields, distinct keys at repeated addresses and rollback on persistence failure.
- [x] 2.3 Extend the existing MapLibre component with creation-only selection, no initial marker, click/keyboard selection and modal resize/error cleanup. Verify one moving marker, correct coordinate order, explicit selection requirement, retry preserving inputs, and unchanged existing Site-detail/public resident map interactions.
- [x] 2.4 Add shared Bin form fields and mutation API helpers, including indexed field errors, complete numeric validation and required carrier/waste dropdowns. Verify each input maps to the planned API field, malformed text such as `1.1abc` cannot submit, valid decimals send JSON numbers, and editable missing values never become `N/A`.
- [x] 2.5 Add the top-right `Pridėti surinkimo vietą` action and scrollable creation modal with required address fields, map and dynamic stable-ID Bin forms. Verify cancel persists nothing, the final form cannot be removed, missing location blocks submission, and pending submission sends only one request.
- [x] 2.6 Wire successful creation back to `/admin/sites` and refresh the current list and overview using revision/request keys. Verify no full page reload, applicable filters remain, statistics include the new Bins, obsolete reads cannot replace fresh data, and failed submission retains values with Lithuanian errors.
- [x] 2.7 Document Site creation payload/response, numeric validation, manual address/key/location meanings and failure/rollback verification in README and the management verification guide. Verify the examples against the running disposable backend and record desktop/320px and keyboard creation evidence; run frontend lint/build after this slice.

## 3. Deliver adding a Bin to an existing Site

- [x] 3.1 Implement `POST /sites/{site_id}/bins`, locking Site before reading inheritance and inserting, returning 201 BinSummary after commit. Verify copied Site coordinates, same-lowest-ID-child address inheritance, preservation of NULLs, legacy empty-Site handling, assigned metadata and missing/invalid/oversized-ID responses through API/SQL.
- [x] 3.2 Add `Pridėti konteinerį` above the Bin list and a modal reusing only the five Bin inputs. Verify there are no editable address/location controls, required inputs/dropdowns work, cancel preserves records and errors/pending states retain focus and values.
- [x] 3.3 Refresh the Bin list and Site statistics after addition and reveal the new Bin under ascending-ID pagination. Verify no full page reload, all-child counts/capacity/groups/carriers update, stale requests cannot overwrite the refresh, and the new Bin's history opens with the normal empty-history state.
- [x] 3.4 Document add-Bin payload, inheritance and verification in the management guide. Verify the documented API calls and UI flow against manual and representative imported Sites, and run frontend lint/build after this slice.

## 4. Deliver transactional hard deletion

- [x] 4.1 Implement `DELETE /sites/{site_id}` with Site locking, database cascades and 204 after commit. Verify Site/Bin/history/resident-request removal, unrelated data preservation, rollback and 404/422 behavior on disposable records through API/SQL.
- [x] 4.2 Implement `DELETE /bins/{bin_id}` with parent-before-child locking, Bin recheck, all-child existence check and final-Site removal, returning 200 `{site_id, site_deleted}`. Verify nonfinal and final deletion, children on other pages, preserved surviving coordinates, dependent cascades, rollback and missing/invalid targets.
- [x] 4.3 Add sibling red `Ištrinti` controls to Site/Bin rows and Lithuanian confirmation dialogs using existing patterns. Verify activating deletion opens neither navigation nor history, cancellation preserves records, consequence text identifies the record/dependents, and focus/pending/error states work by keyboard.
- [x] 4.4 Wire delete completion to list/detail/overview refresh, last-valid-page recovery and final-Bin navigation to `/admin/sites`. Verify filters survive, aggregates update, removed rows do not return through stale reads, 404 has recovery, and refresh failures retry only reads rather than replaying successful mutations.
- [x] 4.5 Document both delete responses, cascades, page recovery and rollback in the management verification guide. Verify commands against disposable fixtures, including resident requests/history, and record controlled two-final-Bin deletions and addition-versus-final-deletion sessions to demonstrate committed Site consistency; run frontend lint/build after this slice.

## 5. Verify the complete management and browsing flow

- [x] 5.1 Run the complete creation/addition/nonfinal deletion/Site deletion/final-Bin deletion flow through the configured application with disposable verification records. Verify 320px and desktop layout, keyboard location selection, dialog focus restoration, map/API failure recovery and preserved browsing/search/pagination/history/public resident behavior; record actual evidence in the management guide.
- [x] 5.2 Run frontend lint/build, focused backend static/syntax checks, Alembic metadata checks on disposable PostgreSQL and `openspec validate bins-ui-update --strict`. Verify all checks pass and no automated test suite, new dependencies, live VASA import, unrelated edits or existing-storage reset have been introduced.

## 6. Apply requested UI refinements

- [x] 6.1 Extract the Truck ghost-style delete button into a reusable row-action component and use it for Truck, Site and Bin rows, preserving independent activation and confirmation.
- [x] 6.2 Move Site creation onto the search/clear row and display only street/house number in Site list rows, preserving filtering and full detail/API addresses; verify desktop and 320px layout.
- [x] 6.3 Add the map title and read-only latitude/longitude fields below house number/postal code, remove below-map selection content, and select the focused map center with Enter/Space; verify blank initial fields, click updates, one marker, keyboard selection and retry behavior.
- [x] 6.4 Update README and verification evidence, run frontend lint/build and strict OpenSpec validation, and verify shared deletion/dialog focus and responsive creation after the refinements.

## 7. Refine coordinate display

- [x] 7.1 Move latitude/longitude immediately below the creation map and disable focus, editing and text selection with disabled styling while preserving map-driven population; update documentation and verify desktop/320px behavior, lint/build and strict OpenSpec validation.
