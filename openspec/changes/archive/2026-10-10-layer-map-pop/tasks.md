# Tasks

Follow [design.md](design.md) and both delta specs. Implementation belongs to `/home/stitas/Projects/viptop-layer-map-pop`; the existing server on port 5174 mounts a different checkout and does not verify this feature.

## 1. Worktree runtime and data

- [x] 1.1 Prepare a temporary Compose configuration from this checkout for project `viptop-layer-map-pop`, with separate named volumes and available alternate ports (proposed frontend/backend/database: 5175/8002/5434); start it and verify healthy services, published ports and build/bind paths pointing to this worktree, without changing the repository's default Compose mappings or the other running stack.
- [x] 1.2 Check required CSV exports and population GeoJSON, run `python -m app.interfaces.table_import` for all available CSVs, then `python -m app.interfaces.bin_population` inside this stack; verify both exit successfully, expected snapshot counts are present, no bin allocation is missing and resident totals are conserved separately per waste type.
- [x] 1.3 Start `docs/population-map-verification.md` with this worktree's runtime commands, actual URLs, project/configuration location and data setup results; verify the recorded import/rebuild order and connection target reproduce the isolated setup without requiring `bin_days` or VASA synchronization.

## 2. Read-only population API

- [x] 2.1 Add population Polygon, property, feature and collection schemas and the population service projection in the existing map modules; verify only the four specified properties are returned, all rings and merged shapes are retained, numeric/suppressed estimates are preserved and missing-density residents project to null without storage writes.
- [x] 2.2 Add `GET /map-analytics/population-cells` using `CollectionSession`; verify this worktree's backend returns ordered unique polygon IDs, its frontend proxy reaches the same response, an empty dataset is a successful empty collection, and database failure remains an error rather than an empty fallback.
- [x] 2.3 Add a repeatable read-only API check with configurable URLs, useful output and nonzero failure exit to the verification guide, and document the endpoint/estimate meaning in README; run the check against the isolated database to compare IDs, geometry and properties with storage, record response size/time and verify documented commands work as written.

## 3. Population renderer and interaction

- [x] 3.1 Add the typed population loader and register `population` / `Gyventojų tankumas` / `polygon` alongside the landfill definition; verify its checkbox and legend appear, no population request occurs while unchecked, and enabling loads through the existing layer session.
- [x] 3.2 Implement the dedicated unclustered GeoJSON fill/outline renderer and shared purple-band definitions; verify the specified threshold boundaries, equal-density colour consistency, suppressed lowest-band handling, merged shapes and holes, and filtering of unknown-density polygons from fills, outlines and click targets.
- [x] 3.3 Implement Lithuanian popup details from original cached features; verify the three fields and number formatting, `<11` source display, assumption derived from stored residents/area, zero-area handling and the declared-residence/estimate explanation.
- [x] 3.4 Implement explicit polygon insertion and point-hit exclusion; verify points and counts stay above polygons for both enable orders, landfill marker/cluster clicks invoke only their existing behaviour, and a polygon click away from markers opens details without moving the camera.
- [x] 3.5 Implement visibility, popup ownership, hover and disposal through the existing renderer contract; verify hiding closes only population details, cached re-enabling does not refetch, recovery uses cached data, and reopening the page leaves no duplicate sources, style layers or event interactions.
- [x] 3.6 Extend the verification guide with a browser walkthrough and representative real polygon IDs/locations for numeric, suppressed, merged and missing-density cases; verify the examples against this dataset and cover the large remainder's interior, polygon holes, density legend and both enable orders.

## 4. Integrated acceptance

- [x] 4.1 Complete the browser walkthrough on desktop and at 320-pixel width using this worktree's frontend; verify map navigation, labels, legend wrapping, popup controls, existing landfill colour/clustering and point priority, and record full-grid loading/render responsiveness and any limitations in the verification guide.
- [x] 4.2 Use browser network controls or local response overrides to verify disabling during a pending read, cached re-enabling, population failure/retry and an empty response; confirm distinct Lithuanian loading/empty/error feedback, preserved camera/other dataset visibility and no stale population features or popup. Record actual results.
- [x] 4.3 Run frontend `npm run build` and `npm run lint` in this stack, rerun the documented API check through backend and proxy, and review the implementation diff; verify checks pass and the feature introduces no migrations, new dependencies or changes to import/allocation code. Record commands and results.

## Workflow follow-up

- Review and archive this change separately after implementation is accepted.
- When integrating `layer-map-bins`, reconcile shared files and the complete selection/extension requirements so both features survive; repeat point precedence checks with bin filters, ordinary clusters and high-zoom overlap groups once that dataset exists in the combined checkout.
