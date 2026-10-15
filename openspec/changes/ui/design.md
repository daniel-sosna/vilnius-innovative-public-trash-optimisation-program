# Design

## Context

See [proposal.md](proposal.md) for motivation and scope. The frontend uses React 19, Vite, Tailwind 4, Radix/shadcn primitives and MapLibre. `src/main.tsx` renders `App` under StrictMode; `App` owns the shared project date and router. `index.css` already maps semantic variables through `@theme inline` and declares light color-scheme. There is no launch gate.

The current logo includes a Leaf icon; city branding uses a bundled WebP. Resident confirmation uses an external GIF, a green check and dispatch wording. Shared buttons default to 36px and use opacity-based hover. Driver fill buttons use saturated utility colors with white text. Analytics popup CSS already consumes semantic theme variables.

Inputs:

| Package | Authoritative material | Application destination |
|---|---|---|
| `/home/stitas/Downloads/VipTop Design Kit.zip` | `tokens.json`, assets/components, previews and implementation notes | `frontend/public/brand/`, `frontend/src/brand/`, compatible logo replacement |
| `/home/stitas/Downloads/VipTop Launch Animation.zip` | packaged player/gate, `clip.json`, readable player/renderer/responsive sources and references | `frontend/public/brand/launch/launch.html`, `frontend/src/brand/launch-gate.*` |

Preview metrics, copy and map screenshots are visual examples. The user confirmed only receipt wording and popup theming as additional decisions. Source inspection found the launch HTML contains four embedded image assets and no remote HTTP URLs; its approximately 6.3 MB size merits cold-load verification. This is source inspection, not browser or device certification.

## Goals / Non-Goals

**Goals:** reuse supplied files, make themes centrally adjustable, preserve component interfaces and workflow state, and keep launch isolation independent from routing and data readiness. Cover all existing pages rather than redesigning only a landing page.

**Non-Goals:** replacing the UI library, introducing a theme engine or animation service, refactoring domain/map hooks, normalizing unrelated product copy, changing backend contracts or creating new product interactions. The proposal defines the full exclusions.

## Decisions

### 1. Extend the semantic theme and preserve Tailwind mappings

Import `brand/theme.css` then `brand/components.css` after `index.css` in `main.tsx`. Preserve Tailwind/tw-animate imports, `@theme inline`, base styles and existing reduced-motion handling. Keep supplied palette/typography/motion/radius variables centralized; add semantic input/success/info/control styling where current components rely on hardcoded utilities.

Use scoped component variants for exact primary hover, white fields, 44px mobile controls and 48px resident submit. Retain compact desktop tables where useful. Preserve Button props, Radix composition, focus and disabled behavior. Existing dormant `dark:` utility variants need not be expanded into a feature; prevent activation of dark appearance and introduce no new dark styling.

Alternative: per-page hardcoded colors is fast initially but creates inconsistent hover/status behavior. Replacing `index.css` risks losing Tailwind and app-specific rules. Shared semantic styling plus targeted page layout adjustments achieves broader coverage with smaller changes.

### 2. Reuse local branding through existing interfaces

Use the supplied `VipTopWordmark` through the existing `VipTopLogo` call sites. Preserve link containers and accessible names. Update `VilniusLogo`'s asset to the supplied transparent PNG while retaining its `className` API and using intrinsic aspect ratio/object containment. Keep both city and VipTop branding readable within mobile navigation.

Use `WolfMascot` only on welcome, suitable empty states and resident confirmation. Copy needed assets from the kit; do not fetch a new font or image, rasterize the wordmark or load the optional sprite atlas unless it is used. Maintain source asset proportions and decorative accessibility defaults. Use Vite `BASE_URL` for new asset URLs.

Alternative: recreate logos/mascot or use external imagery would diverge from the supplied identity and add unnecessary dependencies.

### 3. Mount the packaged launch gate once above App

Keep StrictMode and render:

```text
StrictMode
  --> LaunchGate
        --> App (project date + router + pages, mounted immediately)
        --> fixed launch overlay + isolated iframe
```

Reuse the packaged launch HTML and gate/CSS. Scale the scene proportionally to cover the viewport as requested by the developer; crop outer edges for non-16:9 screens and retain the supplied separate portrait final composition. Preserve the child wrapper's layout compatibility with `h-dvh` map/driver screens. Avoid conditional mounting of App: `inert` and `aria-hidden` provide the interaction barrier while pages initialize. Do not tie dismissal to API completion or store a historical seen flag.

Retain the iframe start/ready/done handshake, expected source/origin/instance validation, idempotent dismissal and effect timer/listener cleanup. The packaged player maps three seconds of real elapsed time to source 13.5–15.0, holds the final frame for 250ms, hides preceding scene elements and hides all artwork until image decoding succeeds, reacts to viewport resize without restarting, and provides a 450ms static reduced-motion branch. Keep the six-second timer measured from active overlay mounting. Timer/frame scheduling means visual completion is on the next available browser frame, not a guaranteed paint at an exact millisecond.

Focus adjustment is a permitted compatibility adaptation: if keyboard focus was on the overlay when the overlay disappears, move focus to the current page's main/heading without remounting it; avoid overriding a page's intentional focus. Verify that root-level dialogs cannot receive focus while their content is inert, especially with portal-based primitives and initial page effects. Preserve the packaged animation rather than inventing another loader.

Alternative: gates inside pages replay during navigation; delaying App mount wastes the animation interval; rebuilding the player risks changing timing and responsive artwork.

### 4. Keep maps protected while styling surrounding UI

Separate CSS/markup presentation edits from MapLibre initialization, layer factories, data hooks and camera/animation logic. Allowed areas include `admin-layout.tsx`, `map-analytics-page.tsx` and scoped popup/sidebar/legend styles in `analytics-map.css`; the user explicitly permits popup surfaces, borders and typography. Popup metric values, text and click behavior remain identical.

Protect MapLibre canvas rendering, native map controls, basemap/style URLs, attribution, sources, marker SVGs, paint expressions and route/polygon geometry. Do not apply generic global SVG/image/button rules that recolor or resize map features/native controls. Where inherited typography could change protected native map appearance, scope branding styles or preserve existing map-local values. Preserve map resize handling as admin header sizes change.

Keep `bin-categories.ts`, adequacy risk mappings and map layer palettes as their existing authoritative sources; the supplied `map-colors.ts` does not justify replacing them. For non-map fill controls, adopt the kit's specified swatches without changing labels or numeric values. Light swatches need dark readable text, not the current blanket `text-white`. Numbers/labels/selected outlines remain available without color.

Alternative: blanket brand-color replacement or copying static preview map markup would violate protected domain semantics and live map requirements.

### 5. Preserve page structure and state during restyling

Use page-specific presentational changes on top of shared primitives:

| Area | Presentation focus | Protected behavior |
|---|---|---|
| Role selection | wordmark, city identity, selective mascot, restrained role buttons | role destinations |
| Admin layout/calendar | light header, active accent, wrapping/mobile sizing | menu keyboard handling, date persistence/locks, map height |
| Trucks/sites/bin details | white forms, restrained tables, readable dialogs | CRUD, filters, pagination, validation/history |
| Resident | mobile branded header, themed service panel, one red submit, local success mascot | lookup/error/retry/pending, fixed location map, POST semantics |
| Driver | theme picker/status/bin steps, large controls, fill swatches | route state machine, navigation map, recorded observations |
| Demo/routes/truck demo | themed pipeline, table and controls | prediction, assignments, pagination, run tracking and animation |
| Analytics | opaque floating controls, sidebar, legend, AI panel and popup surfaces | filters, selection, cached layers, analysis and camera |

For resident success remove external GIF dependence and its decorative failure state, retain API-gated success and accessible status, and use `Pranešimas gautas`. Amend the durable requirement through this change's resident delta, including the scenario elsewhere that explicitly prescribes the GIF. The latest-service panel's visual requirement is updated while its source/ordering/date/absence semantics remain intact. Do not silently fix the pre-existing resident title mismatch or invent dispatch behavior.

Alternative: restructuring pages or replacing whole files from previews would overwrite real workflows, especially active driver/demo/risk work.

### 6. Verify the integrated UI with existing tools

Run `npm run build` and `npm run lint` in `frontend`. Add no automated tests or testing dependencies. Record manual evidence in this change, including widths, routes, loading/error/success states, keyboard behavior, launch timing, requests beneath overlay, failure recovery and map comparisons. Capture a pre-change map baseline for identical datasets/cameras before implementation to detect accidental appearance changes.

Before verification requiring collection data, check configured `VIPTOP_DATA_DIR` for `sites_<digits>.csv`, `bins_<digits>.csv` and `bin_hist_<digits>.csv`; if any is missing, ask the developer to provide exports. Use the documented table importer if loading is needed; never run `bin_sync`. No bin-population rebuild is needed. Use the current application data and workflows rather than reconstructing preview figures.

Only operational asset/setup notes and links to behavior specs belong in `docs/development.md`; manual evidence belongs in `openspec/changes/ui/verification.md`. No README expansion is needed.

## Risks / Trade-offs

- Active driver/demo/risk edits overlap presentation files --> adapt focused markup/style changes to the integrated implementation, retain state hooks/API usage, and review the final diff for unrelated behavior edits.
- Launch HTML embeds large PNGs --> retain the exact package, measure cold readiness and low-power device behavior; automatic dismissal/fail-safe guarantee access. Do not add premature preprocessing or a generic loader.
- Shared control sizing changes header height and map space --> retain flex/min-height constraints and map resize handling; inspect mobile menu open/closed and rotation.
- Portal or page autofocus may bypass the intended inert area --> verify keyboard isolation in representative entry routes and adapt only the gate's focus compatibility if needed.
- Pale fill swatches lose contrast with white labels --> use dark text and explicit number/selection states.
- Real iOS behavior cannot be inferred from emulation --> check actual Safari/iPhone if available and record unverified device coverage without claiming it passed.

## Migration Plan

Deploy frontend assets and bundled code together so the gate's static document is available on the same origin. There is no database migration, API rollout or persisted launch flag. Validate production asset paths as well as development paths. Rollback restores the frontend bundle and assets together; resident requests and all domain data remain untouched.
