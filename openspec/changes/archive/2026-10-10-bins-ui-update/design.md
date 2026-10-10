# Design

## Context

See `proposal.md` for motivation and `specs/collection-site-management/spec.md` for the new observable behavior. Design is needed because this change crosses storage, transactions, API contracts, map interactions and multiple React data areas.

Observed implementation:

- `app/infrastructure/models.py` requires `Bin.external_id`; `fk_bins_site_id` uses RESTRICT. BinHist and resident-request foreign keys already cascade. `Site.bins` already uses `passive_deletes="all"`.
- Site/Bin GET routes use `CollectionSession`, which explicitly sets REPEATABLE READ and READ ONLY, then rolls back its short snapshot. Resident submissions show an existing pattern for a writable dependency and committing before success.
- `services/sites.py` gets all four geographical detail fields from the lowest internal Bin ID, preserving NULLs. Site holds display address and coordinates, not structured address columns.
- Site list, Bin list and Site detail use request keys/revisions and AbortController. Overview has its own retry state and currently does not refresh when another data area changes.
- Site rows are Links and Bin rows are buttons. Truck dialogs already handle validation, pending submission, cancellation, errors and focus. The existing map uses configured style, a bundled MapLibre worker, localized controls and ResizeObserver; NULL coordinates currently prevent rendering, and clicks do not select a location.
- Revision `0005` adds resident requests. Import finalization selects unseen Bins twice, once for affected Sites and once for deletion, without excluding NULL external IDs.

## Goals / Non-Goals

**Goals:**

- Add complete management flows without changing existing GET payloads or browsing snapshots.
- Let database cascades handle dependent data and use one explicit transaction per mutation.
- Enforce new-input completeness without imposing new restrictions on existing source data.
- Share Bin form behavior and map infrastructure where there is concrete reuse.

**Non-Goals:**

- No generic CRUD framework, address schema redesign, synchronization reconciliation system or new dependencies.
- No location editing for existing records. Admin membership changes do not recalculate surviving Site coordinates.
- No live VASA requests or import rerun for implementation verification. The import was a one-time operation; its only code change is a NULL-identity cleanup guard.
- No automated test suite. Repeatable manual API/SQL verification and UI checks provide evidence.

## Decisions

### 1. Minimal migration and unchanged optional storage contracts

Add revision `0006` after `0005` (if the migration head changes before apply, preserve that chain and select the next unused revision). Drop NOT NULL on `bins.external_id`, retain `uq_bins_external_id`, and recreate `fk_bins_site_id` with ON DELETE CASCADE. Existing uniqueness permits multiple NULL external IDs while rejecting duplicate known IDs. Update SQLAlchemy's external-ID annotation/nullability and foreign-key action to match.

Retain the existing BinHist/resident-request cascades and Site passive-deletion relationship. Use explicit database deletion rather than loading all descendants through ORM collections. No positive-capacity CHECK, carrier/waste enum constraint or new NOT NULL is added. The user requested required form inputs, not stricter legacy storage.

Alternative considered: rebuilding collection tables or adding origin/address columns. Neither is needed; existing identity namespaces and NULL external IDs express the distinction without rewriting imported data.

### 2. Narrow create schemas and explicit API responses

Define one reusable Bin-create definition and Site-create request schema. Forbid extra input fields. The five Bin properties are required; strict trimmed strings reject blanks, carrier and waste values use the selected API options, and capacity accepts only a positive finite JSON number. Explicitly reject booleans, numeric strings, malformed/partial numeric text and nonfinite values before persistence. Store numeric capacity in existing NUMERIC without applying display rounding. Frontend conversion must validate the entire value, not use partial `parseFloat` acceptance.

Site-create adds `street`, `sub_district`, `house_number`, optional `postal_code`, finite range-checked latitude/longitude and `bins` with at least one item. Normalize optional postal-code blanks/omission to NULL and preserve textual house/postal formatting. Required string inputs stay descriptive; `object_group` is not a count.

| Endpoint | Body | Success |
|---|---|---|
| `POST /sites` | Site address fields, coordinates, `bins: BinCreate[]` | 201, existing SiteSummary shape: `{id, address, bin_count}` |
| `POST /sites/{site_id}/bins` | One BinCreate definition only | 201, existing BinSummary shape: `{id, inventory_number, waste_type, capacity_m3}` |
| `DELETE /sites/{site_id}` | None | 204, no body |
| `DELETE /bins/{bin_id}` | None | 200, `{site_id, site_deleted}` |

Missing positive identities, including BIGINT overflow IDs, return 404; malformed/nonpositive IDs and invalid bodies return 422. Persistence failures use generic operation errors without SQL details. Static `/sites/stats` remains ahead of dynamic routes. Frontend mutation helpers use existing `/api` proxy conventions and translate API errors into Lithuanian messages, including indexed `bins` validation paths.

Alternative considered: returning 204 for Bin deletion and asking the client to infer parent removal. Returning the committed outcome avoids guessing from a paginated list or issuing an unnecessary parent-existence read.

### 3. Server-owned metadata, manual identity and inheritance

Use server-generated `manual:<uuid4>` Site keys protected by existing unique storage. Do not ask for a key or derive it from address: repeated addresses can represent separate manually selected collection points, and imported `address:`/`unknown:` keys cannot collide. Site display address is trimmed `street house_number, sub_district[, postal_code]`, without an extra separator for NULL postal code.

For Site creation, copy the entered structured address and selected coordinates to every initial Bin. For addition to an existing Site, query its lowest-ID child for all four address fields in one selection and copy the Site's coordinates. Preserve NULL fields; do not fill from another child or parse display address. Legacy empty Sites yield four NULL inherited fields while accepting the five required Bin inputs. No structured Site columns are introduced, and surviving Site display address stays unchanged when its first child is deleted.

For every manual Bin assign exactly the requested district/region/city, NULL external ID, NULL territory type and NULL client count. Initial history and resident requests are empty. Imported capacity units remain the documented source assumption; newly entered capacity explicitly represents m³.

Alternative considered: parsing `Site.address` or adding required Site address columns. Parsing cannot recover absent source values reliably, while new columns would require backfill and expand this feature unnecessarily.

### 4. Writable transactions and final-child consistency

Add a writable collection dependency following the existing resident-request session pattern, using default READ COMMITTED isolation, bounded local lock/statement timeouts, rollback/close on failure and generic persistence error handling. Keep the read-only GET dependency unchanged. Services flush and build response values, then commit once; errors before successful commit roll back all writes.

Site creation inserts Site plus every Bin within one transaction. Database cascades delete history and resident requests when Site or Bin is removed.

Serialize admin membership changes by locking Site before writing its children:

- Adding a Bin locks its Site, checks existence and reads inherited fields, then inserts and commits.
- Deleting a Site locks that Site before issuing its cascading delete.
- Deleting a Bin first resolves its Site ID without locking the Bin, locks Site, then rechecks the Bin's existence/membership before deleting. After deletion, check for any remaining child across the entire Site; delete Site if none remain and commit the resulting `site_deleted` response.

Use the same parent-before-child order to avoid a cycle between Site cascade deletion and individual Bin deletion. READ COMMITTED lets a waiter observe a preceding committed membership change. A missing Site or Bin after waiting returns 404. This handles two final-child deletions and addition competing with deletion without a separate counter or database trigger. The existing public resident-request Bin key-share lock remains compatible with deletion waiting on active submissions.

Alternative considered: count remaining Bins without coordinating writers. Two deletions can each observe the other's Bin and leave an empty Site. Parent serialization is small, explicit and sufficient for the admin endpoints. Import concurrency redesign is outside this one-time-import feature.

### 5. Shared map infrastructure with selection enabled only in creation

Extend `LocationMap` with a selection mode/callback while preserving its existing detail and public resident modes. In selection mode, NULL selected coordinates are valid: render a map centered on Vilnius, with no marker until explicit selection. View center is separate from selected coordinates. Clicks create or move one marker and notify the form using `[longitude, latitude]` correctly. Do not enable marker dragging or install selection listeners outside creation.

Place the title `Spauskite ant žemėlapio, kad pasirinktumėte lokaciją` above the creation map. Show disabled, nonselectable latitude/longitude fields immediately below the map; both start empty and reflect selection. Disable focus, pointer interaction and text selection, with a muted disabled appearance. Keep the area below the map free of other selection copy, status text and buttons. On the focused map canvas, Enter/Space selects its current center after keyboard pan/zoom using the same callback as clicking; describe this shortcut accessibly on the canvas. Maintain configured style, localized controls, worker loading, map error/retry handling, and ResizeObserver for opening/resizing a large modal. Dispose listeners, marker and map on close; map retry does not discard address/Bin inputs or a valid already-selected point. Failure before selection leaves creation disabled.

Alternative considered: a second map library or geocoding widget. Both add unnecessary dependencies and are outside scope; the existing MapLibre runtime can supply selection directly.

### 6. Focused dialogs and explicit refresh signals

Use one shared Bin form for initial Bin sections and the add-Bin modal. Keep stable client form IDs when adding/removing sections so validation/errors track the right Bin. Reuse shadcn/ui Input, Select, Dialog and AlertDialog with the Truck patterns. Create-Site content uses a larger desktop width, viewport-limited height and internal scrolling; on small screens fields stack and the map fits the content width. No editable value or placeholder is literal `N/A`.

Place the Site add action at the right of the address-search/clear row, wrapping only on narrow screens. Site list row text uses the leading street/house-number segment of the stored display address; full addresses remain available in details, confirmations and API responses. Imported addresses already have this short form; manual addresses append comma-separated sub-district/postal text. This display formatting does not participate in storage or address inheritance.

Extract the Truck list ghost-style red `Ištrinti` button into a shared row-action component and use it for Truck, Site and Bin rows. Make delete controls siblings of the Site Link/Bin history button within the row layout. This avoids nested interactive controls and makes navigation/history activation independent of deletion. Confirmation identifies the record, states the hard-delete consequence in Lithuanian and warns about removal of Site when the selected Bin is currently known to be the final child. The backend result remains authoritative if membership changes during confirmation. Focus starts on cancel; closing restores the trigger or a surviving nearby control if that row was removed.

Use existing revision/request-key patterns instead of adding a query library. After Site creation/deletion refresh the filtered Site page and global overview; after Bin addition/deletion refresh Site details/statistics and the Bin page. Navigate to the Bin's page after successful addition so it is visible under ascending-ID pagination. Reset stale selected Bin dialogs as needed, abort obsolete reads, and retain last-valid-page recovery after deletions. Final-Bin deletion navigates to the Site list, whose fresh mount reads the overview. Closing Site creation explicitly returns to `/admin/sites`, refreshes current data and preserves applicable filtering.

Pending requests disable repeated submission and prevent dismissal that obscures completion. Failures retain entered values and allow an explicit retry; no automatic POST retries or idempotency infrastructure are added. A 404 offers refreshed data or navigation away from a missing Site. A successful mutation remains successful if a subsequent refresh fails; only that read is retried.

Alternative considered: optimistic local updates to every count, sum and waste distribution. Refetching existing aggregate endpoints is simpler and avoids inconsistent totals across pagination and imported NULL values.

### 7. Single import compatibility guard

In `_finalize`, add `external_id IS NOT NULL` to both the stale-Bin DELETE predicate and the raw SQL selecting affected Sites. Existing import upserts continue using source IDs and separate Site namespaces. Keep all other import behavior unchanged. Deleted imported data is allowed to reappear under the existing explicit import contract; do not create tombstones or suppression storage.

Verify this predicate on disposable local records without invoking VASA. No import lifecycle features or source-dependent checks are needed for acceptance.

## Risks / Trade-offs

- [Hard deletion removes resident requests as well as history] → Preserve the existing cascade and describe the dependent deletion in confirmation copy; verify unaffected Bins retain their records.
- [Manual and imported Sites can share a displayed address] → Keep independent namespaces and document no automatic deduplication; creation represents an explicitly chosen Site.
- [Imported Site coordinate may no longer equal remaining Bin mean after admin deletion] → Admin management deliberately preserves stored markers; averaging remains an import-only behavior. Document this distinction without adding editing.
- [Deleting the lowest-ID Bin can change displayed/inherited address metadata] → Keep the existing first-child contract and refresh Site details; do not silently synthesize or persist replacement address fields.
- [Map resources or WebGL fail] → Preserve inputs, show localized retry and require explicit valid selection.
- [Lock contention causes timeout] → Short transactions, consistent lock order, rollback and recoverable errors; verify the final-child cases with controlled disposable sessions.
- [A network failure can hide an already committed POST] → Prevent double-clicks and automatic retries; operators can inspect refreshed records before choosing a retry. Idempotency tokens are outside this MVP.

## Migration Plan

1. Implement and verify the new revision against disposable PostgreSQL containing representative imported, nullable, history and resident-request data. Confirm unchanged records, identities and uniqueness before enabling mutations.
2. Apply the existing Alembic startup/upgrade path with existing PostgreSQL storage retained. No reset, seed or import is required. Deploy backend then frontend, packaging the revision and preserving configured map style.
3. Verify Site-plus-Bins creation, both delete paths and browsing using records created for verification; never delete the imported registry as a verification fixture. Check migration metadata with `alembic check` and record actual results.
4. Rollback: rolling back application code alone must not re-enable the old importer cleanup against manual data. Prefer keeping the compatible schema while resolving application issues. Schema downgrade must first check that no NULL external IDs exist, refuse otherwise with an actionable diagnostic, and restore RESTRICT/NOT NULL only when compatible. Never delete manual records to force downgrade; deleted hard-delete records require restoration from retained backup if recovery is needed.
