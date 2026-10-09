# Design

## Context

See `proposal.md` for motivation and `specs/` for behavior contracts. At the start of the volume work, `Truck` in `backend/app/infrastructure/models.py` has generated integer identity, text name, integer site-count capacity, availability and retirement flags. Revision `0003` imposed capacity 1–99 plus nonblank-name and deleted/unavailable checks; `0004` replaced collection storage while retaining trucks. `backend/start.sh` upgrades the schema before serving.

Truck HTTP schemas/router are under `backend/app/interfaces/trucks/`, with queries/mutations in `backend/app/services/trucks.py`. Services project the same fields for list, detail, create and patch, apply filters before counting/pagination, and exclude retired rows. `/trucks/stats` independently computes whole-fleet totals and average capacity.

The frontend already groups the page, fetch/types helper, editor, delete dialog and overview under `frontend/src/pages/trucks/`. It uses shared Radix/shadcn-style Select/Dialog/Input components, existing toast feedback and shared `TablePagination`. Mobile rows already switch from table layout to a compact grid. Nearby collection screens demonstrate Lithuanian `m³` formatting; their domain-specific helpers need not be imported into Trucks.

For revision `0005`, the user confirmed the target fleet was empty. The volume/carrier and numeric-input work has since been implemented and verified. The landfill extension must also support trucks subsequently created at `0005`, retaining them as unassigned; the user confirmed selection is required when creating/editing. This is a stated deployment precondition, not a measured live result: local API/Docker access was unavailable during exploration. The existing `collection-records` Truck requirement and `truck-management` API/UI requirements explicitly describe site counts and need the accompanying deltas. Earlier migration-specific preservation requirements still describe revisions `0003`/`0004`; this change adds a separate transition rather than changing those historical promises.

## Goals / Non-Goals

**Goals:** Change the existing persisted-to-browser contract together, keep retirement atomic, prevent invented migration data, and reuse the current interface. Separate unrestricted text storage/API values from the current select choices.

**Non-Goals:** Compatibility conversion from site counts, speculative backfill machinery, new service layers/dependencies, changes to collection importing or Bin units, and optimizer integration. Future optimization must consume the volume contract; it is not invoked or implemented here.

## Decisions

### 1. Use required NUMERIC volume and TEXT carrier

Replace the old capacity column with `max_volume_m3 NUMERIC NOT NULL`, mapped as `Decimal` using the existing SQLAlchemy Numeric support already used for Bin volumes. Do not impose a fixed precision/scale that would round accepted fractional input on write. Use `waste_carrier TEXT NOT NULL` without an enum, allowed-values CHECK, catalog foreign key or name-limiting constraint. Keep generated Truck identity, name validation, availability, deletion default and the deleted/unavailable invariant.

Replace `ck_trucks_capacity_range` with a volume validity check requiring a positive finite value, explicitly excluding numeric NaN and infinities. A simple `> 0` alone does not establish the complete finite-value invariant. Carrier blank-string validation remains in the application; do not add carrier database checks.

Alternatives: an integer would reject fractional m³; DOUBLE PRECISION storage would be simpler but diverge from the existing volume-storage convention; retaining the old numeric value under a new name would invent a unit conversion. An enum would unnecessarily bind future company names to schema changes.

### 2. Validate the new mutation contract without coercing invalid JSON types

Create requires the five editable fields including an existing positive integer `landfill_id`. PATCH uses optional fields with the existing explicit-null rejection and `exclude_unset` semantics. Preserve `extra="forbid"`, strict string/boolean validation, name trimming and duplicate-name allowance. Carrier uses the same strict trimmed nonempty-string behavior as name, without an API four-value whitelist.

Volume input must be an actual finite JSON number greater than zero: integers and fractions succeed, numeric strings and booleans do not. Keep this distinction explicit at validation rather than depending on a coercive numeric type. HTTP and frontend use ordinary numeric values; ORM persistence uses Numeric/Decimal. Response schemas serialize volume and fleet averages as JSON numbers, not Decimal strings. Normalize serialization consistently across all four response-producing CRUD paths. Storage has no old 99 cap or fixed-scale rounding; wire values follow the existing browser/JSON number convention rather than an arbitrary-precision string contract.

Alternative: restrict the API to the four UI carriers. Keeping a nonblank string contract better matches the user's future-name requirement and allows directly stored future values to be read. The four-option list belongs in one truck-specific frontend constant shared by the modal and filter. This is the planning default stated in the proposal.

### 3. Keep queries, pagination and retirement in the existing service

Update the projected Truck fields to exactly the six response fields. `deleted` remains in storage and all eligibility predicates, not the normal response or payload. Keep list envelope, ascending-ID order, page size 10, name escaping, transactions, status codes and PATCH/DELETE concurrency behavior.

| Contract | Result |
|---|---|
| `GET /trucks` | Existing paginated envelope; optional `name`, `available`, `min_max_volume_m3`, `max_max_volume_m3`, `waste_carrier`, `page` |
| `GET /trucks/stats` | `{total, available_count, average_max_volume_m3}` for all nondeleted trucks |
| `GET /trucks/{id}` | Six-field representation or 404 |
| `POST /trucks` | Five required editable fields; 201 representation |
| `PATCH /trucks/{id}` | Any subset of editable fields; 200 representation or 404 |
| `DELETE /trucks/{id}` | Atomic deleted=true/available=false; bodyless 204 or 404 |

Parse volume bounds as finite positive numeric query values and reject inverted intervals with field-addressable 422 detail. Trim carrier filters and use literal equality; blank carrier has no effect. Apply all predicates to both count and items. API filters can query any carrier text, while the UI exposes the four options plus `Visi vežėjai`. Remove old query parameter definitions without compatibility aliases. Keep `/stats` before the dynamic ID route and change AVG to the new volume field, returning its unrounded numeric result or null.

Alternative: replacement Truck endpoints or a client-side filtered fleet would duplicate existing behavior and break current server pagination/statistics expectations. Updating the existing contract is smaller and more reliable.

### 4. Extend the existing Truck components

In `api.ts`, update Truck/TruckStats types, replace `isSiteCapacity` with positive finite volume parsing/validation, map new field errors, and define the shared carrier choices. Keep HTTP error/toast behavior. Numeric editor/filter text is distinct from API JSON numbers: accept a decimal comma or point, normalize before validating/sending, reject blank input, and never treat an empty string as zero. Restrict typing and paste to numeric text in the editor and both filters, retaining the previous value when nonnumeric text is entered. Allow temporary empty/unfinished numeric input for normal editing, including scientific notation for small stored values; positive finite validation still applies before saving or querying. A decimal-friendly input must not retain `min=1`, `max=99` or integer-only stepping.

In `truck-editor.tsx`, retain modal focus/pending/cancel behavior, preload volume and carrier, use supplied labels, show `m³` beside the volume input, and add the existing Select primitive for carrier. New forms have no carrier default. Remove the old site-count helper and errors. If an API/direct database value is outside the four options, display its stored text separately, leave current selection empty and require deliberate selection before saving. Do not add that name as a selectable fifth option or silently replace it. Partial API updates remain available independently of this full-form behavior.

In `trucks-page.tsx`, add carrier query state, request parameter, active-filter detection, clear/reset handling and pagination identity. Replace capacity bounds and labels with `Talpa nuo (m³)` / `Talpa iki (m³)`. Add a carrier column between volume and availability; use the existing compact mobile row layout with readable carrier wrapping. Preserve availability icons, delete behavior, action order and table editing.

Format row values using `lt-LT` with `m³`, preserving useful fractional precision without rounding saved data. Do not blindly use the collection formatter's fixed three-decimal display if it would hide a small positive value as zero. Keep the overview's existing one-decimal display policy and append `m³`; use `Vidutinė maksimali talpa`, retaining the empty `—` and independent retry behavior. Existing Lithuanian error copy can be adapted to `Įveskite skaičių, didesnį už nulį.` and `Pasirinkite atliekų vežėją.`.

Alternative: rebuilding the screen or creating a global carrier registry would expand scope without helping this vertical slice. Existing UI primitives and page-owned state cover the change.

### 5. Preserve the complete supplied landfill catalog

Create `landfills` in revision `0006`. Use generated INTEGER identity starting at 1; insert the three features in file order so initial IDs are 1, 2 and 3 and the next generated ID is 4. Retain the original feature ID in unique `source_id TEXT`. Separate Point coordinates as `longitude DOUBLE PRECISION` and `latitude DOUBLE PRECISION`, in the source's longitude/latitude order; check geographic ranges. Store all source properties as named columns: required TEXT `name`, `operator`, `address`, `facility_role`, `status`, `coordinate_quality`, `coordinate_source`, `facility_source`; nullable TEXT `municipal_arrangement_source` and `current_status_source`; required `waste_streams TEXT[]` and `verified_at DATE`. Preserve the collection's name and description in required `dataset_name` and `dataset_description` TEXT on each row. No GeoJSON `type` field or redundant geometry object is stored.

The supplied file contains three facility points, not confirmed route assignments. Preserve its English names, uncertainty descriptions, source URLs, waste-stream array order and dated verification claims verbatim. Treat them as source data rather than instructions or new operational guarantees. All three rows are offered in the dropdown. The migration embeds a self-contained snapshot of the mapped data, with the source filename and SHA256 `1e588cb980c105d287497f202fc4e342d9fee3940d2e37fda7a586d68185e42b`, and never accesses Downloads or HTTP at runtime. Missing properties become NULL, not invented text. Repeated startup does not reinsert seeds.

Alternative: raw JSON-only storage hides the requested coordinates and property contracts; relying on a local Downloads path or live URLs makes migration nonreproducible. Three rows of collection metadata are simpler than an additional metadata table.

### 6. Require explicit landfill assignment without inventing existing assignments

Add nullable INTEGER `trucks.landfill_id` with a foreign key to `landfills.id`, `ON DELETE RESTRICT`. Existing active and retired trucks retain every field and get NULL. Reads include `landfill_id` (integer or null) as the sixth response field; it remains editable, whereas `deleted` does not. POST requires a strict positive integer referencing an existing landfill; supplied PATCH values have the same validation and reject explicit null. For an assigned truck, omitted PATCH keeps its assignment. For an unassigned truck, a nonempty PATCH requires a valid `landfill_id`; `{}` returns the unchanged eligible truck. Unknown IDs return field-addressable `422` without mutation; missing/deleted Truck behavior remains `404`. No carrier/operator matching, landfill default or availability changes are introduced. Retiring a truck retains its assignment.

Expose read-only `GET /landfills` as an unpaginated JSON array of complete mapped records ordered by ID. Follow existing backend HTTP/schema/service boundaries and transaction/error handling without adding catalog write endpoints or dependencies. Truck list filters, columns and fleet statistics retain their existing behavior.

In the existing editor, load the catalog on open with cancellation on close and a local retry state. Add `Sąvartynas` using the current Select, option labels from each exact stored `name`, and numeric IDs in payloads. New/unassigned forms start blank; edits preload an assignment after lookup succeeds. No option is selected automatically. Loading, failure and empty catalogs prevent saving with concise Lithuanian status/error/retry text while preserving other entered values; cancel remains usable. Missing selection shows `Pasirinkite sąvartyną.`. Make long option/trigger names wrap within the modal at 320px and retain keyboard/focus/pending-submit behavior.

Alternative: a NOT NULL column with a default would invent truck destinations or block valid existing fleets. Nullable storage plus required application selection meets the confirmed transition policy.

### 7. Permit unknown landfill details

The user's nullable-field follow-up supersedes revision 0006's required detail fields. Revision `0007` relaxes all landfill columns except generated `id` and `name`: coordinates, original source ID, dataset metadata and facility details may be unknown independently. Preserve types, nonnull source-ID uniqueness and coordinate range checks; NULL passes these checks. Preserve all seeded values and Truck references, with no backfill or defaults. Update ORM, API and frontend types together; lookup returns explicit null details and still offers the required name/ID for truck selection. Leave the already usable revision 0006 unchanged. Downgrade locks the catalog and refuses rows with NULL in any newly relaxed field before restoring its NOT NULL constraint, identifying affected IDs without inventing values or changing data.

## Risks / Trade-offs

- Site counts cannot identify real volume or carrier --> The migration requires an empty legacy table and never seeds synthetic truck facts or clears records automatically.
- Database writes can race with a preflight --> Lock the truck table within the migration transaction before checking and altering it, following the existing migration pattern.
- Frontend/backend contract versions can disagree --> Deploy both together; update current examples/OpenAPI and verify all representation paths.
- Numeric coercion or Decimal serialization can violate the wire contract --> Manually verify integer/fraction inputs, string/boolean rejection and numeric JSON responses from list/detail/create/patch/stats.
- The storage/API allow future names the UI cannot select --> Render the stored name faithfully and require explicit current-option selection on modal save.
- Carrier filtering introduces a fifth filter and table column --> Keep current responsive wrapping, check desktop and 320-pixel keyboard operation, and do not change shared layout structure.
- Bin volumes are raw source values with an unverified unit assumption --> Do not compare them to Truck volume or change optimizer/importer behavior in this change.
- Facility source descriptions and coordinates have uncertain operational meaning --> Preserve the supplied provenance; no optimizer or external verification is implied.
- Existing trucks lack landfill assignments --> Keep NULL until an explicit edit; fail invalid selections with field detail.
- Runtime access was unavailable during discovery --> Record actual migration/API/browser verification results during apply, including any environment blockers; planning validation alone is not runtime evidence.

## Migration Plan

1. Create a new Alembic revision after `0004`, provisionally `0005`; do not modify historical revisions. Upgrade from initialized `0004` storage before creating demo trucks with the new contract.
2. In the migration transaction, lock `trucks` and check all rows, including retired ones. If populated, fail with IDs and an explanation of the missing volume/carrier facts; no automatic deletion, mapping or fabricated defaults. If this deployment assumption changes, revise the plan before implementation proceeds.
3. For an empty table, drop the old range constraint/column, add required volume/carrier columns and volume validity constraint, and keep all other Truck schema objects. Touch no collection tables or import records. Fresh installations run the normal migration chain without imports.
4. Deploy the matching backend/frontend contract together. The existing startup path migrates first and refuses serving on failure. Current documentation must use new fields and distinguish historical migration checks from checks at the new head.
5. Verification uses disposable databases: fresh upgrade; populated collection data with empty trucks; an unexpected legacy truck causing rollback; repeated upgrade after new trucks exist; and `uv run alembic check` for model drift. Check unrestricted carrier storage separately from UI choices.
6. Rollback of this new revision is permitted only when `trucks` is empty, with the same transactional guard. Restore the old required integer column/range constraint and remove volume/carrier columns without touching collection data or identity generation. Refuse rollback if any truck exists, including retired rows: volume cannot be converted back to a site count, and dropping carriers loses data. This does not alter revision `0004`'s existing refusal to downgrade further.
7. Update README and current manual verification procedures; retain historical/archived evidence. Run the existing frontend build/lint checks and manual API/UI verification rather than introducing automated test files.

8. Revision `0006` creates/seeds landfills and adds the nullable Truck FK in one transaction, retaining populated `0005` fleets and collection/import records. Verify seed values against the source, generated IDs/sequence, fresh and initialized upgrades, repeated startup and `alembic check`.
9. Downgrade `0006` refuses any assigned truck, including retired ones, before changing schema; lock Truck storage during the check. If no assignment exists, remove the FK/column and catalog, preserving unassigned Truck and collection values. Leave `0005` and earlier migration guarantees unchanged.
10. Deploy lookup and Truck API/UI together; verify all three choices, required selection, lookup failure/retry, partial assignment semantics, restart persistence and existing volume/carrier/filter/retirement behavior with disposable storage.
11. Revision `0007` relaxes landfill detail columns for both fresh installs and databases already at `0006`; preserve seeded rows/references. Verify name-only storage and lookup, coordinate/source constraints, complete and incomplete downgrade behavior and ORM agreement. Deploy matching nullable API/frontend types.
