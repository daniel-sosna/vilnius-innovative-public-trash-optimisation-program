# Proposal

## Why

VipTop needs a complete persistent fleet-management workflow and a clearer overview of fleet readiness. The truck UI, ten-row pagination, fleet statistics and screen/use-case grouping are implemented. This revision improves save feedback, action-button consistency, overview typography and mobile navigation while retaining that workflow.

## What Changes

- Keep role selection at `/` and public administration at `/admin/trucks`, with a shared navbar containing `Šiukšliavežės`. Replace the VipTop truck brand icon with an eco-friendly leaf on both screens.
- Below 640 pixels, collapse admin navbar links into a keyboard-operable hamburger menu that closes on selection or Escape.
- Widen the shared admin content area from approximately 1024 to 1280 pixels, aligning the title, statistics, filters, action row and table. Use a neutral gray page background with green accents and retain responsive usability at 320 pixels.
- Place `Pridėti šiukšliavežę` followed by `Išvalyti filtrus` in a right-aligned row above the table. Both buttons are always visible and have equal width and height; clear has a filled background.
- Add a fleet overview above the filters/table: total nondeleted trucks, average maximum site capacity, and available percentage inside a circular indicator with a proportional green arc. Statistics cover the whole nondeleted fleet, independently of table filters/pages.
- Display the available/total count, such as `24 iš 27`, with the same font size and weight as the total and average card values.
- **BREAKING**: reduce the list's fixed page size from 20 to 10. Retain previous/next controls and add a labeled page-number input with Enter/`Eiti` navigation, preserving filters.
- Change the capacity column and mobile equivalent to `Max Aikštelių per reisą`. Capacity still counts collection sites; the modal keeps `Maksimalus aikštelių skaičius per reisą` and its site/container helper.
- Preserve persistent CRUD, strict validation, available-by-default creation, confirmed atomic retirement, deleted-truck exclusions, stale-response protection, failure/retry states and mutation-driven page recovery.
- Replace inline create/edit success feedback with a success toast entering from the top right; failed saves show an error toast. Preserve field validation beside inputs, failed-save values and separate list/statistics refresh-error retry controls.
- Group frontend components by screen and backend interfaces by use case; extract pagination as a small reusable component for future tables.

## Capabilities

### New Capabilities

- `truck-management`: Administrator navigation, Lithuanian fleet overview and truck UI, CRUD/statistics API, filtered pagination with page-number navigation, validation, soft-delete visibility and interaction/error states.

### Modified Capabilities

- `collection-records`: Required Truck deletion flag, capacity 1–99 and deleted/unavailable consistency, distinction between physical deletion and soft retirement, and safe storage upgrade with historical attribution preserved.

## Impact

- Backend: retain the Truck model, migration `0003`, focused service and application-owned sessions. Group truck router/schemas under `app/interfaces/trucks/` and bin-sync CLI under `app/interfaces/bin_sync/`, preserving `python -m app.interfaces.bin_sync`. Add one aggregate statistics query without GIS I/O or a new migration.
- Frontend: group truck-specific UI under `pages/trucks/`; retain shared primitives/layout/branding outside screen folders. Add reusable pagination, the fleet overview, aligned wider layout and gray theme background using existing dependencies. The latest refinement adds shared accessible save toasts using the existing Radix dependency, mobile navbar disclosure, equal action dimensions and overview typography.
- Shared contracts: `GET /trucks` still returns `{items, total, page, page_size}`, now with `page_size=10`. Add `GET /trucks/stats` returning `{total, available_count, average_max_bins_per_trip}` for nondeleted trucks. The average is null for an empty fleet; the UI derives the available percentage.
- Historical route queries continue joining retained trucks regardless of retirement. No route endpoint or route generation is introduced.
- Documentation: update README and manual verification during implementation for the new statistics contract, ten-row examples, page jumps, action placement, file grouping and retained bin-sync invocation, plus save toasts, equal buttons, count typography and mobile-menu interaction.
- No driver screen, authentication, bins/routes UI, route generation, optimisation engines, ML, restore, GPS, maintenance, configurable page-size infrastructure or additional deployment.

Confirmed refinements: leaf branding, wider aligned layout, gray background, always-visible right-aligned add/clear actions with a filled clear button, ten-row pagination, direct page navigation, reusable pagination, screen/use-case grouping, fleet overview and the revised column label. Approved design choices: statistics use all nondeleted trucks rather than filtered rows; average displays one decimal, percentage displays a rounded whole number while its arc uses the actual ratio; an empty fleet displays 0 total, — average and 0% available.

Further confirmed refinements: top-right create/edit success and error toasts, equal-width/equal-height add and clear buttons, available/total counts matching the other overview values, and navbar links inside a hamburger menu below 640 pixels. Toasts support dismissal and accessible announcements, remain visible above dialogs, and fit small viewports. A committed save stays successful if a subsequent read refresh fails. This refinement changes no backend or database contract.

Existing migration risk remains: incompatible capacities/names fail with actionable diagnostics and no silent corrections. The layout/statistics refinement needs no schema change; the collection-records delta remains applicable.
