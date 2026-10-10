# Proposal

## Why

The role-selection screen, shared admin navbar, and public resident-request page currently lack the supplied Vilnius identity. Adding the same city logo in these three places makes the application's connection to Vilnius visible throughout its entry and request flows.

## What Changes

- Show the full supplied Vilnius emblem and wordmark centered near the top of `/`, above the existing role-selection content.
- Show a compact version on the right of the shared admin navbar, with VipTop branding on the left, on all admin routes.
- Show the logo centered above the title on `/resident-request/:bin_id` during loading, lookup errors, not-found, ready, and pending submission states.
- Preserve the logo's red artwork, transparency, and aspect ratio, with an accessible Lithuanian description and layouts usable at 320px width.
- Proposed defaults from exploration: retain VipTop's leaf branding, use approximately 96px image height on public pages and 40px in the navbar, and retain the resident success screen without the logo. Exact spacing can be tuned during visual verification.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `truck-management`: Extend role-selection and shared admin branding requirements with the Vilnius logo and its placements, preserving the existing navigation and eco branding.
- `resident-requests`: Add centered city branding above the public request title before success, while preserving the standalone route and success replacement behavior.

## Impact

- Frontend only: `frontend/src/pages/role-selection/role-selection-page.tsx`, `frontend/src/components/layout/admin-layout.tsx`, and `frontend/src/pages/resident-request/resident-request-page.tsx`, plus one shared logo component and a bundled image asset.
- Source asset: `/home/stitas/Downloads/Logo_of_Vilnius.svg.webp`; inspected as a 960x960 RGBA WebP with transparency. Implementation will copy it into the project, so deployed pages do not rely on the Downloads path or an external image host.
- No API, database, routing, dependency, or infrastructure changes are needed.
- No material technical uncertainty remains. The exact rendered spacing and navbar fit at narrow widths require visual verification during implementation.
