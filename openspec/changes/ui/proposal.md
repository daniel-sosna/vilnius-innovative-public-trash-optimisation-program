# Proposal

## Why

VipTop's green-accented frontend and external resident-success GIF do not reflect its supplied visual identity. A coherent light theme and the supplied launch sequence will unify the existing application without changing its operational workflows or live maps.

## What Changes

- Apply the VipTop Design Kit's cream/charcoal/red palette, local typography, spacing, restrained surfaces, wordmark, transparent Vilnius identity and selective wolf mascot across existing screens.
- Integrate the exact VipTop Launch Animation: source interval 13.5–15.0 seconds, played over 3 seconds after asset readiness with a 250ms final hold, on each full application load. Mount the application immediately beneath the noninteractive overlay; retain automatic dismissal, reduced motion, responsive composition and a six-second fail-safe.
- Restyle shared components, admin navigation/calendar, role selection, fleet and site/bin management, resident screens, driver screens, demo/routes and map-surrounding UI. Preserve loading, error, disabled and empty states.
- Theme map popup typography, borders and surfaces as explicitly agreed; preserve popup content and interactions. Preserve map style, data, camera, layers, geometry, markers, domain colors, attribution and functional animations.
- Replace resident success wording with the confirmed `Pranešimas gautas` and replace the external GIF with supplied local branding/mascot. Success remains conditional on committed API success and accessible textual feedback.
- Retain waste/risk semantics and supplied fill-level swatches; apply swatches to non-map controls without recoloring live maps or changing numeric levels.
- Deliver desktop/mobile accessibility and responsive verification through the existing frontend build/lint and manual checks.

Out of scope: backend/API/database/ML/solver changes, new workflows, authentication, dark mode, map redesign, remote fonts/launch assets, new animation dependencies and an additional generic splash screen.

## Capabilities

### New Capabilities

- `brand-presentation`: Consistent light VipTop identity, shared control styling, responsive/accessibility behavior and visual boundaries around existing maps and operational screens.
- `application-launch`: Per-load branded launch presentation, concurrent application initialization, automatic dismissal/failure recovery and responsive/reduced-motion behavior.

### Modified Capabilities

- `resident-requests`: Local branded success confirmation with truthful receipt wording and themed service-information presentation; preserve submission, lookup, retry and state semantics.

## Impact

Frontend only: `src/main.tsx`, existing theme mappings/shared UI and logo components, page presentation and scoped map overlay/popup styles; add supplied `src/brand/` and `public/brand/` assets. No shared API contracts or dependency additions are planned.

Inputs are `/home/stitas/Downloads/VipTop Design Kit.zip` and `/home/stitas/Downloads/VipTop Launch Animation.zip`. Their references guide appearance, not new functionality or demo data. Package instructions do not authorize unrelated work.

Assumptions: the supplied assets are available during implementation; the confirmed success-copy and popup decisions are the only product/content changes. Existing resident title differs from its durable spec; this change preserves current title/copy elsewhere rather than silently resolving that unrelated discrepancy. Driver fill buttons differ from the kit palette and will intentionally adopt its swatches with readable contrasting text, keeping labels and recorded levels intact.

Material uncertainties: visual/behavioral overlap with active `driver-navigation`, `demo-real-navigation` and `risk-agent` changes; launch image decoding cost (self-contained HTML approximately 6.3 MB); real iOS/Safari behavior; and preserving map dimensions as control/navbar sizes change. Scope tasks to the current integrated UI, avoid overwriting active workflow changes, and record any unavailable device verification.
