# Tasks

The developer confirmed that all verification was completed personally and
authorized marking every task complete. Verification is developer-reported;
see `verification.md` for the confirmation and available recorded evidence.

## 1. Real prediction API and runtime

- [x] 1.1 Add explicit demo input/product path settings and prerequisite validation; check the configured data directory for required sites/bins/bin-history exports before data-dependent work and request missing exports rather than running bin_sync. Locate the trusted delivered model, normalization artifact, enriched CSV, registry and population CSV without regeneration; verify paths and product dependency metadata, and report missing ML artifacts to the developer before live inference work.
- [x] 1.2 Add the product-compatible CPU inference dependencies to backend configuration/lock and copy `viptop_fill` into the Docker image; verify locked installation/image imports and that ordinary API startup remains usable with unconfigured demo artifacts. Record installed versions against the supplied product metadata.
- [x] 1.3 Implement `POST /demo/predictions` and its Pydantic contracts using existing `predict_csv`, September input validation, levels >2, short database identity/coordinate reads and explicit prerequisite/data errors; verify a real September 14 request reports September 15, registry coverage and matching due counts without source/model/plan writes, and invalid date/timestamp requests fail before inference.
- [x] 1.4 Add the frontend prediction API client with abort handling and a 15-minute deadline, configure matching dev/preview proxy deadlines, and protect backend inference from overlapping expensive scans; verify a real roughly five-minute response reaches the client, unrelated API reads work during inference, and busy/timeout failures are actionable.
- [x] 1.5 Provide a repeatable non-UI check command under `app.interfaces.demo` for a requested date, printing forecast date, evaluated/due/mappable counts, duration and meaningful exit codes; verify it invokes the real predictor and matches endpoint selection. Extend `docs/data/fill-prediction.md` with runtime prerequisites, mounted path configuration, invocation, accepted duration and side effects, linking specs for contracts; verify documented commands/path resolution against the configured environment. Do not add an automated test suite.

## 2. Shared date and first Demo slice

- [x] 2.1 Add the App-level date provider/hook with September validation, September 14 default, local persistence and owner-scoped nonpersisted run lock; verify navigation/refresh retain the day, invalid storage recovers, storage denial stays usable, and date-only values remain stable across timezones.
- [x] 2.2 Add the navbar calendar icon and accessible September-only grid, preserving mobile navigation and logos, and consume the hook in Map Analytics without changing its request behavior; verify September bounds, keyboard use and 320px layout, and that date changes preserve analytics camera/layers and do not start agent analysis.
- [x] 2.3 Add `/admin/demo`, its navigation link, date context, prominent start action and explicit workflow hook/state; connect real prediction, clear old outputs on start/date change and lock start/calendar during active stages. Verify the first vertical slice with real loading, September 14 -> September 15 context, duplicate-start prevention, empty/error states and cleanup on navigation/reload.
- [x] 2.4 Reuse the existing MapLibre lifecycle for predicted-bin rendering, stable definitions, configurable accessible labels and narrow readiness/render acknowledgement support; verify only due mappable bins display, missing coordinates are disclosed, zero mappable bins stop appropriately, and restart updates sources without recreating the map. Manually verify existing Map Analytics layers after the shared-map extension.
- [x] 2.5 Extend `docs/development.md` with demo launch/setup configuration and local request-timeout considerations, linking the behavior specs instead of reproducing UI rules. Update only applicable README feature/pipeline rows; verify links resolve and README remains below 150 lines.

## 3. Road navigation and progressive routes

- [x] 3.1 Implement the replaceable navigation service contract, road-following OSRM implementation, `POST /demo/navigation` and matching Pydantic/TypeScript DTOs with ordered path and explicit site/bin assignments; verify deterministic grouping over up to 150 available nondeleted stored trucks, exact once-only coverage of mappable input bins, one-stop handling and clear no-fleet/invalid-input failures.
- [x] 3.2 Extend the repeatable demo check command to exercise road navigation and report assigned trucks, stop/bin counts and coverage; verify identical inputs produce identical results and all assigned identities come from the real input/database. Document the command in `docs/development.md` and disclose the road-service configuration and demo assignment assumptions without restating behavioral contracts.
- [x] 3.3 Connect automatic navigation after predicted markers render, with compact completed/active/failed stage feedback and OSRM/OpenStreetMap attribution; verify visible stage ordering and that navigation failure retains predicted markers, releases controls and exposes no successful table.
- [x] 3.4 Add route sources/layers and a cancellable progressive drawing controller using distance interpolation and stable colors; verify simultaneous partial-to-full growth, labels/bin readability, one-stop route completion, roughly four-second duration, reduced-motion handling and cleanup on restart/unmount/map failure without hundreds of DOM elements.
- [x] 3.5 Reveal the concise assigned-truck table only after all current-run drawing completes, deriving counts from stop/bin assignments and linking accessible rows to truck-demo routes; verify table gating, stored names, color associations and correct counts for shared sites; paginate at five rows per page and reset pagination for each run.

## 4. Truck-driving demonstration

- [x] 4.1 Add `/admin/demo/truck/:truck_id` using the shared layout, existing stored-truck lookup, road-resolved shared fixture, title Šiukšliavežės sekimas and shared navbar navigation without page-local return/replay controls; verify direct load/refresh and multiple truck IDs use the shared implementation, with actionable invalid/missing-truck context.
- [x] 4.2 Animate truck movement, stop pauses and collected-bin visuals using the shared map lifecycle; verify ordered collection, camera following, variable slower movement, final-position hold and timer/frame disposal on navigation, 320px usability and no database mutations or project-date lock.

## 5. Integrated manual verification

- [x] 5.1 Record a full real run in `openspec/changes/demo/verification.md`: September selection -> real prediction wait -> due markers -> road calculation -> progressive routes -> table -> truck-driving animation. Include actual dates, counts, runtime, prerequisite locations and observed outcomes; verify source/model inputs and collection-plan records remain unchanged.
- [x] 5.2 Record September 30 -> October 1, refresh/navigation persistence, lock through every active stage, restart after completion, date change after completion, missing model, zero due bins, navigation failure/no fleet, map/drawing failure and navigation away during inference/animation. Use controlled verification inputs or browser response interception for otherwise unavailable failure cases without introducing a runtime fake predictor; verify obsolete responses cannot update another run and every terminal path unlocks controls.
- [x] 5.3 Run frontend build/lint, the repeatable demo check and OpenSpec validation; manually check existing fleet/site pages and Map Analytics layer interactions after shared changes. Record results in this change and resolve failures; no automated tests are added.

## Developer-requested Demo corrections

- [x] 6.1 Render road-following OSRM paths without straight-line fallback and use finite routing deadlines; developer verifies geometry and routing failures.
- [x] 6.2 Disable clustering on the Demo maps, preserving Map Analytics defaults; developer verifies individual points.
- [x] 6.3 Populate the stored Demo fleet to 150 trucks and assign up to 150 nonempty routes; developer verifies counts and exact bin coverage.
- [x] 6.4 Paginate truck results at five rows per page and remove the requested disclaimer and Aptarnauti label; developer verifies pagination, restart and mobile layout.

Implementation for 6.1–6.4 is delivered and developer verification is confirmed.

## Developer-requested truck-following corrections

- [x] 7.1 Resolve the shared driving fixture through OSRM road legs; developer verifies movement and road alignment without straight-line fallback.
- [x] 7.2 Follow the truck with the map camera and use slower variable travel/stop timings; developer verifies camera, speed changes and navigation cleanup.
- [x] 7.3 Use title Šiukšliavežės sekimas and remove truck name, disclaimer, counters, completion/color explanation and return/replay buttons; developer verifies presentation and mobile layout.

Implementation for 7.1–7.3 is delivered and developer verification is confirmed.

## Developer-requested predicted-bin appearance animation

- [x] 8.1 Reveal predicted mappable bins in randomized order, adding batches of 1, 1, 1, 2, 2, 2 and subsequent triplets of doubled batch sizes, with slower decreasing delays, final-render navigation gating, accurate visible counts, reduced-motion handling and cancellable timers; developer verifies the appearance sequence, stage/date lock and navigation cleanup.

Implementation for 8.1 is delivered and developer verification is confirmed.
