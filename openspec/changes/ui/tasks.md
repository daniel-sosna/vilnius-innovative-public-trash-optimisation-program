# Tasks

Browser/device verification is assigned to the developer by explicit request.
Checked implementation tasks track delivered code; their manual acceptance
clauses remain pending in [verification.md](verification.md). Browser-only
tasks remain unchecked until the developer records results.

## 1. Theme, assets and welcome slice

- [ ] 1.1 Before data-dependent verification, check configured `VIPTOP_DATA_DIR` for `sites_<digits>.csv`, `bins_<digits>.csv` and `bin_hist_<digits>.csv`; stop and ask for missing exports. Use `python -m app.interfaces.table_import` per `docs/data/import.md` only if import is needed, never `bin_sync`. Capture baseline screenshots/settings of existing analytics, driver, demo and location maps in `openspec/changes/ui/verification.md` for later comparison; verify baseline data/camera and current active-change state are recorded.
- [x] 1.2 Copy required Design Kit assets/components into `frontend/public/brand/` and `frontend/src/brand/`; import theme/components CSS after `index.css`, preserving Tailwind mappings and base rules. Verify local asset paths and computed palette/font/radius against `tokens.json`, including OS dark preference retaining a light theme.
- [x] 1.3 Adapt shared Button/Input/Select/Dialog/AlertDialog/Switch/Toast presentation for exact primary hover, semantic states, white fields, readable borders, mobile targets and bounded dialogs without changing props or behavior. Verify representative keyboard focus, disabled/error states, 44px mobile targets and reduced-motion styling; add no automated tests.
- [x] 1.4 Reuse the supplied wordmark through `VipTopLogo`, update `VilniusLogo` compatibly and restyle role selection with a selective mascot. Verify both role links, logo accessible names, aspect ratios, 320/390px and desktop appearance; record evidence in this change.
- [x] 1.5 Update `docs/development.md` with local brand/launch asset locations, CSS import ordering and links to the behavior specs (delta paths until archived). Verify paths resolve and the notes contain operational setup information rather than duplicate behavior or manual verification instructions.

## 2. Application launch slice

- [x] 2.1 Integrate packaged `launch.html`, `launch-gate.tsx` and CSS above `App` under StrictMode. Preserve exact playback, isolated iframe, validated handshake, inert/aria-hidden behavior and six-second timer. Verify App mounts beneath the overlay, no launch storage flag exists, no new dependency/remote asset is introduced and map/page sizing survives the wrapper.
- [ ] 2.2 Verify `/`, direct admin, direct driver and direct resident routes plus hard refresh play once per load, while internal links do not replay. Measure ready/start/completion for 3-second elapsed playback plus a 250ms final hold; verify page API/map initialization begins before dismissal and local loading remains afterward. Record timings/network observations in `verification.md`.
- [ ] 2.3 Verify keyboard/pointer isolation, automatic dismissal and valid focus after dismissal, including portal-based UI. Adapt only gate compatibility where necessary; verify StrictMode leaves no stale listeners/timers or repeated playback.
- [ ] 2.4 Verify launch-document/image failure and missing-completion cases through browser request blocking or transient debugging without committed test code; confirm access recovers by six seconds from mounting. Verify unrelated source/origin/instance messages are ignored and record results.
- [ ] 2.5 Verify reduced motion shows final composition for approximately 450ms, desktop/tablet/Android/iPhone/small-phone portrait and landscape fit without stretching, and rotation retains elapsed playback. Check actual iOS/Safari when available; record any device coverage limitation distinctly from passed emulation checks.

## 3. Admin and management screens

- [x] 3.1 Restyle `admin-layout.tsx` and project calendar with light surfaces, wordmark and red active treatment. Verify every existing route link, mobile menu open/close/Escape/focus behavior, shared date persistence and lock behavior, and map dimensions with the menu expanded at phone/tablet widths.
- [x] 3.2 Restyle trucks list/overview/editor/delete dialog and pagination using restrained tables and forms. Verify existing filtering/pagination, create/edit/delete validation and disabled/error states through the running app; record representative mobile/desktop evidence.
- [x] 3.3 Restyle sites list/detail/overview/bin tables, bin form/history, collection editor/delete dialog and pagination. Verify existing filters, CRUD/history/collection actions, long labels, nullable values, dialog fit and table-local scrolling without changing queries or data semantics; record evidence.

## 4. Resident request slice

- [x] 4.1 Restyle resident loading/ready/not-found/failure/pending states with the VipTop/city header, cream/light layout, themed latest-service information and one 48px red submit. Preserve existing title, field order, fixed map and API handling. Verify direct QR entry, missing/invalid bin, retry, null fields, latest-date display/absence, duplicate-click protection, error recovery and phone safe areas.
- [x] 4.2 Replace external success GIF and dispatch wording with local supplied mascot/branding, semantic green status and exact `Pranešimas gautas`. Verify success appears only after committed API success, prior form/map disappear, artwork failure preserves text/status, no submit returns in that session, reload permits a new request and reduced motion remains readable; record evidence.

## 5. Driver and demo presentation

- [x] 5.1 Restyle driver picker, start/loading/error/completed views, next-stop and confirmation panels without changing workflow hooks or navigation map. Verify map-dominant navigation, large mobile controls, route-follow/truck movement and existing back/save/error recovery remain intact; compare map rendering with the baseline.
- [x] 5.2 Apply supplied non-map fill swatches to driver level controls with contrasting text, numbers, labels and selected state. Verify all five values retain the existing advance/back/correct/confirm/save behavior and map/route palettes are unchanged; record phone and reduced-motion evidence.
- [x] 5.3 Restyle `/admin/routes` DemoPage and truck-demo shell/table/controls, retaining existing route aliases. Verify prediction/navigation/drawing stages, assigned-truck pagination, unserved/loading/error output, date locking and actual road/truck animation; compare protected map features with baseline and record evidence.

## 6. Map surroundings and popup presentation

- [x] 6.1 Restyle analytics headers, opaque floating buttons, shared sidebar, layer controls, legends, selection actions and AI panel using scoped presentation edits. Verify layer/filter/analysis state survives switching/closing, keyboard focus restores, panels scroll within bounds and attribution/native controls remain reachable at 320/390px, tablet and desktop widths.
- [x] 6.2 Theme popup typography, borders and surfaces without changing metrics, labels, conclusions, provenance semantics or interactions. Verify representative bin/group/adequacy popups, long content and keyboard actions; confirm inherited styles do not alter protected native map controls, marker SVGs or canvas/layer colors.
- [ ] 6.3 Compare all existing map surfaces, including site/detail and resident location maps, with matching baseline data/cameras. Verify style URLs, tiles, sources, layer paint/domain colors, markers, clusters, polygons, route geometry, attribution, selection and camera behavior remain intact; record screenshots and a focused diff review in `verification.md`.

## 7. Integrated acceptance

- [x] 7.1 Run `npm run build` and `npm run lint` in `frontend`; fix introduced failures and distinguish any pre-existing failure with evidence. Verify no automated tests/dependencies or backend/domain-contract edits were added; record commands and outcomes in this change.
- [ ] 7.2 Perform the final cross-screen pass at 320/390px, a tablet width and 1440px, with keyboard and reduced motion: role selection, admin/calendar, truck/site/bin/collection management, analytics, demo/truck demo, driver and resident states. Verify no page overflow, clipped dialog, unreadable label, inaccessible target or obstructed map information; complete `verification.md` with passed checks and remaining device limitations.

## Workflow follow-up

- Archive after implementation and review, syncing the accepted new brand/launch specs and resident deltas. Update the development-doc links to the resulting durable specs when archiving.
