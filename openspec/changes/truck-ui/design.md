# Design

## Context

See `proposal.md` for motivation and the delta specs for behaviour. The persistent vertical slice and first refinement are implemented: React routes and shadcn components connect filtered ten-row pages, reusable direct pagination, CRUD and whole-fleet statistics to FastAPI/PostgreSQL. Alembic revision `0003`, strict validation, conditional retirement, request-scoped sessions and manual integration verification are present. The admin area is approximately 1280 pixels wide with neutral gray surfaces, leaf branding and always-visible right-aligned add/clear actions. Frontend screen components and backend interfaces are grouped by screen/use case.

The latest confirmed refinement replaces inline save feedback with top-right success/error toasts, makes add/clear dimensions equal, enlarges the available/total count to match other overview values and collapses mobile navbar links behind a hamburger toggle. Existing restrictive route references, retirement invariants and historical joins remain applicable. Shared settings include GIS configuration, but server startup and truck requests continue making no GIS requests. The new presentation changes require no backend, database or pagination-contract changes.

## Goals / Non-Goals

**Goals:** Preserve the demonstrable persistent workflow while improving fleet visibility, save feedback and mobile navigation; make ten-row pagination reusable for future tables; group screen/use-case files without extra architectural layers; keep retirement, migration and API contracts reliable.

**Non-Goals:** No generic CRUD framework, repository abstraction hierarchy, application-wide state library, cursor pagination or configurable page-size infrastructure, optimistic-update framework, audit schema or deployment platform. Product exclusions are in the proposal. Historical joins are verified at the persistence layer, not exposed through new route endpoints.

## Decisions

### 1. Extend Truck and preserve restrictive references

Add required boolean `deleted` with a database default of false. Replace the capacity check with 1–99, add a nonblank-name check, and add the invariant `NOT deleted OR NOT available`. Keep the generated identity and Route foreign key unchanged. Soft deletion is one UPDATE setting both flags; API services never call SQL DELETE for Truck.

Database checks protect direct writes and concurrent operations; validation only in React would leave invalid state reachable through API/SQL. Physical deletion of referenced records remains prohibited, while retiring such a truck becomes valid. Future routing eligibility is `deleted=false AND available=true`; future historical route queries join the retained Truck without this eligibility filter. Neither future workflow is implemented here.

### 2. Reuse synchronous database helpers with clear ownership

Create one application-owned engine and session factory in FastAPI lifespan and dispose the engine on shutdown. Provide a request-scoped Session dependency that closes its session and rolls back failures. Group the truck router/schemas under `app/interfaces/trucks/` and retain the focused service under `app/services/`; reuse the ORM model under `app/infrastructure/`. Use synchronous request handlers for synchronous database work.

API schemas validate input and serialize output; the service owns queries, conditional updates and transaction boundaries; routers translate missing records and storage failures into HTTP responses. This fits the existing package structure without introducing unused domain/repository layers. Startup uses the existing migration entrypoint and shared settings; no truck operation performs GIS I/O.

For PATCH and DELETE, include `deleted=false` in the UPDATE predicate and obtain the saved values using RETURNING. A zero-row result means `404`. Commit before returning success. This prevents a stale form from updating a row retired by another request; a read-then-unconditional-update approach would allow that race. Empty PATCH reads the eligible row and returns it unchanged.

### 3. Define a small explicit API contract

| Endpoint | Input | Success | Missing/deleted ID |
|---|---|---|---|
| `GET /trucks` | Optional name, availability, capacity bounds and one-based `page` | `200`, `{items, total, page, page_size}` with items ordered by ID | Not applicable |
| `GET /trucks/stats` | No table filters or pagination | `200`, `{total, available_count, average_max_bins_per_trip}` | Not applicable |
| `GET /trucks/{id}` | Positive integer ID | `200`, Truck | `404` |
| `POST /trucks` | Name, capacity, explicit availability | `201`, saved Truck | Not applicable |
| `PATCH /trucks/{id}` | Any subset of name/capacity/availability | `200`, saved Truck | `404` |
| `DELETE /trucks/{id}` | Positive integer ID | `204`, no body | `404` |

Truck responses contain exactly `id`, `name`, `max_bins_per_trip`, `available`, `deleted`; management Truck representations always have `deleted=false`. POST has no implicit API availability default: the confirmed default belongs to the create form, which sends true unless changed. Duplicate names are permitted.

List pagination uses a fixed size of 10 and `page=1` by default. Apply all filters and `deleted=false` before computing total and retrieving items with ascending ID order, offset `(page - 1) * 10` and limit 10. Return the requested page, `page_size=10`, total matching count and items. Validate page as a positive integer; invalid values return `422`. A valid out-of-range page returns empty items with its actual total, letting the UI recover. Do not expose a page-size control or load the full fleet merely to paginate in the browser.

For example, 21 matching trucks produce ten items on pages 1 and 2, then one on page 3; each response reports total 21 and page_size 10. The count predicate must be identical to the item predicate, so deleted/nonmatching trucks never inflate page totals. Simple offset pagination fits previous/next controls and the existing SQLAlchemy stack; cursor pagination would add complexity without improving this small administrator list.

Use strict JSON string/integer/boolean validation for mutation fields, reject null and unexpected fields, and trim names before checking emptiness. PATCH must distinguish omitted fields from invalid explicit nulls. Query strings are parsed as boolean/integer query parameters, not subjected to JSON strictness; invalid ranges and inverted intervals return `422`. Escape wildcard characters in the SQL name predicate to preserve literal case-insensitive substring semantics. Combine filters with AND and always include nondeleted eligibility.

Retain conventional validation responses for `422` so the frontend can map field locations to Lithuanian messages. Missing rows use `404`; unexpected persistence errors use a generic `500` response and sanitized server-side diagnostics. Do not return raw database exceptions. A typed frontend request helper handles JSON responses and bodyless DELETE success.

These status codes, literal substring matching, inclusive ranges, duplicate names, ID ordering and empty-patch behaviour are planning defaults. Pagination uses one-based pages and a count-bearing envelope as design defaults. Confirmed product decisions include capacity by site, create-form availability enabled, exclusion of deleted trucks from management reads/edits, a maximum of 10 trucks per page, previous/next buttons and direct page-number navigation.

### 4. Add browser routing and a same-origin API proxy

Add React Router browser routing for `/` and `/admin/trucks`, with a shared admin layout containing the navbar and content outlet. The root administrator button performs navigation; the driver button is visible and disabled. Unknown paths can offer a simple return to `/`. Keep admin access public.

Have the browser call `/api/trucks` and `/api/trucks/{id}`. Configure Vite development and preview proxies to forward `/api` to FastAPI, stripping that prefix so public backend endpoints remain `/trucks`. Use server-only `VIPTOP_API_PROXY_TARGET`, defaulting to `http://127.0.0.1:8000` for native development and set to `http://backend:8000` in Compose. Browser code never uses the Compose hostname.

This avoids a CORS configuration and works with current Vite/Compose infrastructure. A future production static host would need an equivalent proxy and SPA fallback; adding that deployment is outside this slice. Verify direct navigation/refresh through the existing development server and preview path.

### 5. Use local UI state and refetch persisted results

The truck page owns current filters, current page, fetched items/total, loading/list-error state, selected edit/create mode and deletion target. Use a small typed fetch helper and normal React state; no query/state dependency is needed for a single screen. Debounce name search briefly and cancel or ignore superseded list requests. Validate bounds before requesting. Treat filters and page as one request identity; reset to page 1 when changing or clearing filters. Do not allow an earlier response or a pre-mutation response to replace newer items or pagination metadata.

After a committed mutation, close its dialog and fetch using current filters and page. Compute the last valid page as `max(1, ceil(total / page_size))`; if the current page exceeds it, update the page and refetch the last valid page. Apply the same recovery to ordinary refreshes after changes made elsewhere. For example, deleting the only item on page 2 of 11 matches returns the user to page 1 of the remaining 10; zero matches settle at page 1. Treat mutation success and subsequent refresh failure separately; a refresh error must not encourage resubmitting a committed create. Disable pending mutation actions, keep form values on failed save, and keep deletion context on failed delete. Determine empty/no-match states from total zero and active valid filters, not a temporarily out-of-range page's empty items. Existing stale rows must not masquerade as fresh results after a list error.

Place `Ankstesnis puslapis` and `Kitas puslapis` near the list footer with `Puslapis X iš Y`, displaying at least one page for an empty result. Previous is disabled on page 1; next is disabled when `page * page_size >= total`. Both are disabled while loading, when total is zero or when the list has failed, until retry succeeds. Page navigation preserves all filters and uses backend requests rather than a full reload. Keep page state local for this slice; shareable page/filter URLs are not required.

Create state starts with blank name/capacity and availability true every time; edit preloads the selected row. Client capacity validation rejects fractions and enforces 1–99 rather than relying on the input's visual limits. If a concurrently retired truck produces `404`, show a concise failure and allow refreshing/dismissing the dialog.

Refetch is preferable to optimistic updates here because backend filtering can remove an edited row and persistence failures must be visible. No full page reload or fabricated sample fleet is needed.

### 6. Build a restrained accessible layout with shadcn/ui

Use the needed shadcn/ui primitives: Button, Input, Label, Select, Switch, Dialog, AlertDialog and shared toast primitives backed by the existing Radix dependency, using the existing aliases and theme tokens. Use semantic navigation and table markup with responsive CSS. Keep a name button inside each row as the keyboard edit target; pointer row activation opens the same modal. Delete must stop propagation and never trigger editing. Use Lucide check/cross icons inside coloured circles, with the requested accessible availability text.

Use an admin container with `max-w-7xl` (approximately 1280 pixels). Align the navbar content, heading, overview, filters, actions and table to that width with responsive side padding. Place `Pridėti šiukšliavežę` followed by `Išvalyti filtrus` in a right-aligned row after filters and before the table. Both use the same Button size, font size and padding; equal-width grid tracks or equivalent styling give them equal width as well as height. Clear is always mounted with a filled neutral background; it resets filters/page even when filters are already blank. Actions wrap in the same order at 320 pixels, retaining equal dimensions and fitting their labels. Keep names wrapping and dialogs scrollable. Restore dialog focus to the initiating control or the relocated add action when a row disappears.

Use the existing Lucide leaf icon for VipTop branding on role selection and administration; retain shared branding outside screen folders. Change background/muted surface tokens to neutral grays, retaining green primary/availability accents and readable contrast. No bitmap asset or dependency is needed. Use `Max Aikštelių per reisą` for the table and mobile equivalent, keeping the longer modal label and agreed site helper. Retain `Prieinamas`/`Neprieinamas`, plural filter labels and Lithuanian navigation/status/error text.

### 7. Aggregate the whole nondeleted fleet

Add `GET /trucks/stats` before the dynamic `/{truck_id}` route so `stats` is never parsed as a truck ID. Use one SQL aggregate query over `deleted=false`: COUNT for total, a filtered COUNT for available_count, and AVG(max_bins_per_trip). Return the arithmetic mean as a number without display rounding, or null for no eligible trucks. Return counts as zero for an empty fleet. Reuse existing session ownership and sanitized persistence-error handling. Statistics accept no table-filter/page contract.

This gives an honest whole-fleet overview without fetching every paginated truck in the browser or changing the existing list envelope. The statistics total can differ from the filtered list total by design; label the overview as fleet-wide. Compute no predicted capacities and persist no aggregate fields.

Display three compact overview blocks above the filters: `Šiukšliavežių iš viso`, `Vidutinis maksimalus aikštelių skaičius per reisą`, and `Prieinamos šiukšliavežės`. Use Lithuanian number formatting with one fractional digit for the average; null renders —. Compute availability as available_count / total, with zero when total is zero. Show a rounded whole percentage in the centre of a small SVG circle; use the unrounded ratio for its green stroke length over a neutral track. Include accessible availability text and handle 0%/100% without special invented data. An inline SVG needs no chart library.

Use the same `text-3xl font-semibold tabular-nums` typography for the total, average and available/total count (for example, `24 iš 27`) below its title. Keep the count distinct from the percentage inside the circle. Allow the availability card to wrap its content as needed at narrow widths rather than shrinking this value or overflowing the viewport; retain the accessible indicator and empty `0 iš 0` count.

Load statistics independently of page/filter requests and keep their own loading/error/retry state. Successful POST/PATCH/DELETE invalidates both overview and list; filters/page changes only affect the list. Cancel or ignore obsolete statistics requests following mutations. Failures show a Lithuanian error rather than fake zeros or stale values presented as freshly fetched. A statistics refresh failure does not replace a committed save's success toast with a save-failure toast; keep the overview's error/retry control and retry only the statistics request. Separate requests may observe concurrent changes at slightly different instants; no cross-endpoint frozen snapshot is promised.

### 8. Extract controlled pagination with a page input

Place a reusable pagination component under shared `components/`, outside truck-specific folders. It receives current page, page size, matching total, disabled/loading state and a page-change callback; it owns only the temporary page-input text and validation. It makes no API requests and contains no truck filters or truck types. Its caller owns fetching, filter resets, stale-response handling and last-page recovery.

Keep previous/next buttons and the current-page indicator. Add an input labeled `Puslapis` and an `Eiti` submit button; Enter submits the same form. Validate a nonblank finite integer within 1..lastPage before calling the callback. Invalid text/range shows a Lithuanian field message without a list request or current-page change. Synchronize the input after caller-driven page changes, including previous/next, filter resets and recovery. Disable submission for loading, errors, invalid filters or no results; display at least page 1 for zero matches. Derive lastPage from the supplied page_size rather than a hardcoded ten.

This extracts the concrete table controls the user expects to reuse without creating a generic data-table framework, shared query store or configurable backend page-size system. Keep the page limit fixed at ten; do not add a page-size selector.

### 9. Group files by screen and interface use case

Move the truck page and its editor, delete confirmation and overview components under `frontend/src/pages/trucks/`. Keep truck-specific request/types helpers with the screen where appropriate; shared UI primitives, layout, branding and pagination remain outside screen folders. Other single-screen components follow the same grouping convention. Update imports and remove superseded flat files rather than keeping forwarding duplicates.

Group backend truck HTTP router and schemas under `app/interfaces/trucks/`, updating the app router import. Move the existing bin-sync CLI into `app/interfaces/bin_sync/` with a `__main__.py` entrypoint delegating to its CLI main function. Preserve `python -m app.interfaces.bin_sync`, exit codes, engine ownership and explicit-only GIS behavior. Retain the current services, database helpers, models and integration clients in their existing layers.

The refactor changes source organization, not CRUD semantics or importer behavior. Verify imports, frontend lint/build, API startup and the bin-sync module invocation on controlled disposable input. Update README/manual verification in the affected task groups. No generated skill files are modified.

### 10. Present save results through shared accessible toasts

Build a small shared toast component/provider using Toast primitives from the already installed `radix-ui` package. Mount its viewport in the shared admin layout, outside truck dialogs, so a successful save can close its modal without removing its feedback. Keep toast UI outside the truck screen folder; the editor/page supplies Lithuanian messages and success/error variants. This reuses an existing dependency without introducing a notification service or global application-state library.

On successful POST/PATCH, show `Šiukšliavežė išsaugota.` as a success toast, remove the inline save-success paragraph and refresh the list/overview. On a failed save request, show a sanitized Lithuanian error toast and preserve the editor and its entered values. Retain validation messages beside inputs, including backend field-error mapping. Trigger feedback only from the mutation result, not from render or read-retry handlers. Pending duplicate prevention remains in place. Deletion feedback is outside this toast refinement.

Place the viewport at the top right with padding and a width constrained to the available viewport. Animate entry from that corner and honor reduced motion. Layer feedback above dialog overlays/content so errors are visible while the editor stays open. Provide a labeled dismiss control and accessible success/error announcements without taking focus. Use the primitive's timed dismissal and pause behavior, with a modest default duration; exact duration is an implementation detail. Verify dismissal and announcements alongside dialog focus management at 320 pixels.

Keep list/statistics read failures and retry controls in their existing areas. A failed refresh after a committed save does not mean the save failed; its retry must neither repeat the mutation nor emit another save toast. Success feedback may dismiss normally while the failed read remains actionable.

### 11. Collapse mobile navbar links into a disclosure

In the shared admin layout, retain inline navigation at the existing `sm` breakpoint (640 pixels and above). Below it, show the brand and a hamburger button; links are initially hidden and expand in a compact panel within the header. Use a simple disclosure with local open state and existing Button/Lucide icons rather than another dependency or a modal drawer. Keep links in one shared definition for desktop and mobile.

Give the toggle a Lithuanian accessible label, `aria-expanded` and `aria-controls`; hidden links must not be keyboard reachable. Selecting a mobile link closes the disclosure. Escape closes it and returns focus to the toggle. Maintain ordinary link semantics, active-route indication and visible keyboard focus. Ensure navigation changes and crossing back to mobile do not leave an unexpectedly open menu. Verify 320-pixel layout, keyboard opening/selection/Escape and desktop visibility without changing public routing.

## Risks / Trade-offs

- Existing capacity above 99 or blank names -> fail migration with IDs and reasons; require deliberate correction instead of truncation or invented data.
- Offset pagination can shift items between requests when another administrator changes the fleet -> use stable ascending ID order, refetch current results and recover an out-of-range page; no frozen multi-page snapshot is promised.
- Public administrator routes -> consistent with the requested no-authentication MVP; do not add authorization infrastructure here.
- Current truck name/capacity edits affect what later historical joins display -> no snapshots are introduced; historical identity/reference is preserved, not past attribute values.
- Development proxy depends on the process environment -> document native/Compose targets and verify both; do not use the browser's localhost for container-to-container traffic.
- PostgreSQL substring matching depends on database collation -> manually verify Lithuanian characters and case matching on the configured database.
- The page-size contract changes from 20 to 10 -> update frontend/backend and documented examples together, using response page_size for calculations.
- Aggregate statistics and filtered totals have different scopes -> label the overview clearly and verify filters never alter it.
- Interface folder moves can break CLI/module imports -> preserve the published bin-sync invocation and verify it independently of truck startup.

## Migration Plan

1. Add reviewed Alembic revision `0003` after `0002`. Before changing schema, query for invalid capacities and blank names; identify incompatible IDs and fail. Keep checks aligned with the API's name semantics, without rewriting existing names.
2. In the normal PostgreSQL migration transaction, add non-null `deleted` with server default false, replace the capacity constraint and add name/invariant checks. Preserve all IDs, other fields, foreign keys and tables. Migration failure prevents serving through the existing entrypoint.
3. Apply and verify on empty and initialized disposable databases; rerun preparation and `alembic check`. Exercise an incompatible fixture to confirm migration failure rolls back every schema change and preserves values.
4. Deploy the updated backend and frontend together through existing Compose, supplying the frontend proxy target. The confirmed overview/layout/pagination refinement requires no new migration: retain `0003`, introduce the statistics endpoint and change page_size to 10 together. Verify frontend dependency volumes and the retained bin-sync module path. Native operators run `uv run alembic upgrade head` before serving.
5. For rollback, prefer retaining the additive schema. Do not run the old application against retired trucks because it cannot respect `deleted`. An explicit downgrade to `0002` must refuse while any truck is deleted; otherwise it removes the new constraints/column and restores the positive-capacity check without deleting records. Verify downgrade only on disposable storage. Do not auto-restore trucks to permit rollback.

Manual verification will use disposable, explicitly synthetic fixtures, including a Route/RouteStop/ServiceEvent chain referencing a truck. After API retirement, management reads return no truck while a SQL join still resolves its identity/name and all referenced rows remain unchanged. Document repeatable requests, expected responses and browser checks; do not add automated test files.

The latest toast/button/typography/mobile-menu refinement is frontend-only. Retain the installed backend and migration `0003`; rebuild/restart the frontend through existing native or Compose commands during implementation verification. Record these checks separately from the previously completed ten-row integration checks.
