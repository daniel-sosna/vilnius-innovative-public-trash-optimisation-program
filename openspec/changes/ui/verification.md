# UI implementation and verification

## Ownership

The developer explicitly took responsibility for browser/device verification and
instructed the agent to implement without waiting for a connected browser.
Implementation tasks are checked for their code deliverables; their manual
acceptance clauses remain assigned to the developer. Browser-only tasks remain
unchecked. No browser checks or screenshots are claimed as passed.

## Baseline

- `VIPTOP_DATA_DIR` is unset in the environment and root `.env`; the configured
  directory is `backend/data/`.
- Required exports exist: `sites_202610092000.csv`, `bins_202610091935.csv`,
  `bin_hist_202610091935.csv`. No import, sync or population rebuild was run.
- The frontend responds at `http://localhost:5173`; the backend responds on 8000.
- Active changes at implementation start: `ui` 0/23, `driver-navigation` 11/16,
  `risk-agent` 8/23, `demo-real-navigation` 9/10. Git's only initial untracked
  content was `openspec/changes/ui/`.
- Browser discovery returned no available browser. Map screenshots, matching
  data/camera baselines and browser/device evidence are unavailable.

## Implemented

- Supplied local theme, wordmark, city artwork and selective wolf components;
  Arial typography, cream/white surfaces, red primary/hover and semantic green
  success. Shared controls have white fields, bounded dialogs, mobile target
  sizing and reduced-motion presentation. Dark utilities were removed from
  shared controls and analytics surroundings to retain the light appearance.
- Role selection, admin/calendar, management forms/tables/pagination, resident,
  driver and demo presentation use the shared theme. Calendar scrolls locally
  where seven 44px columns cannot fit. Management hooks and API calls are retained.
- LaunchGate wraps App under StrictMode without conditional child mounting.
  It retains the packaged source/origin/instance handshake and six-second
  fail-safe. Compatibility additions cover layout, inert body portals, keyboard
  isolation and focus restoration. No storage flag was introduced.
- Resident success uses `Pranešimas gautas`, local wolf/wordmark and green status.
  The external GIF was removed. Submission guards and success API handling are
  retained; failed artwork hides independently of the confirmation text.
- Driver controls use the five supplied swatches with dark labels on light
  swatches and white labels at level 4. Numeric values and workflow callbacks
  are unchanged. Next-stop presentation uses an opaque white surface.
- Analytics surroundings and popup typography/borders/surfaces are themed.
  Popup content and map/domain rendering implementations are retained.
- Operational asset and CSS ordering notes are in `docs/development.md`.

## Command and source checks

- Baseline `npm run build`: TypeScript passed; Vite failed with EACCES removing
  `frontend/dist/assets/index-CxDSXhKd.css`. This output-folder permission issue
  predates the edits.
- Final `npm run build -- --outDir /tmp/viptop-ui-build` from `frontend`: passed
  TypeScript and production bundling. Vite reports its large-chunk warning.
  Public brand assets, including the launch document, are present in the output.
- Baseline and final `npm run lint`: identical six errors and two warnings:
  `pages/demo/api.ts` lines 24/26 (`preserve-caught-error`),
  `pages/map-analytics/map-analytics-page.tsx` lines 30/68 (`refs`,
  `set-state-in-effect`), `pages/map-analytics/use-adequacy.ts` lines 14/39
  (same rules); warnings in `components/maps/analytics-map.tsx` line 33 and
  `use-adequacy.ts` line 42. No new lint findings.
- `git diff --check`: passed.
- The launch HTML retains packaged artwork and playback. Its viewport scale
  uses cover (`Math.max`) rather than contain (`Math.min`) at the developer’s
  request for a full-screen animation. The iframe is absolutely inset to its
  overlay; landscape edges may crop while artwork retains its proportions.
  Portrait final composition and elapsed playback are retained. Browser
  verification of full-screen coverage remains assigned to the developer.
- All referenced local brand artwork exists. The packaged player uses elapsed
  3-second playback plus a 250ms final hold, a 450ms reduced-motion branch and image decode handling.
- Focused diff review: no backend, dependencies, automated tests, map style
  configuration, map layer factories, domain palettes, navigation map,
  location map, route animator or workflow hooks changed. The truck-demo diff
  changes only heading presentation, retaining its marker/road/animation code.

## Developer acceptance remaining

Use the acceptance clauses in `tasks.md` as the checklist. In particular:

- Task 1.1: record map data/cameras and baseline screenshots where available.
- Tasks 1.2–1.4 and 3.1–6.2: verify each implemented screen's workflows,
  keyboard focus, loading/error/disabled states, dialogs, nullable/long values,
  filtering/pagination/CRUD, date locking and state persistence.
- Tasks 2.2–2.5: direct routes and refresh/internal navigation; launch elapsed
  timing and concurrent API/map initialization; automatic dismissal and focus restoration;
  portal isolation; blocked document/images and missing completion; unrelated
  messages; reduced motion and rotation.
- Task 6.3: compare every live map with matching data/cameras and verify domain
  colors, geometry, markers, attribution, native controls and camera behavior.
- Task 7.2: complete the cross-screen pass at 320px, 390px, tablet and 1440px;
  keyboard/reduced motion; safe areas and portrait/landscape. Actual iOS/Safari
  and Android device coverage is unverified, separately from browser emulation.

Record results here before marking the verification tasks complete or archiving.

## Launch frame integrity source checks

- All four embedded PNG payloads pass strict Base64 decoding, Pillow PNG
  integrity verification and full pixel decoding. No image data was rewritten.
- Artwork stays hidden until the ready player starts, preventing partially
  decoded images from appearing. Stage children other than the red wipe and
  closing composition are hidden, excluding truck/bin/other scene flashes.
- Source 13.5–15.0 plays over three seconds with a 250ms final-frame hold.
  Reduced motion retains its 450ms static branch; the six-second access
  deadline remain intact. Full-screen viewport scaling is retained.
- Browser frame-by-frame verification remains assigned to the developer.
