# Design

## Context

See `proposal.md` for motivation. This change touches three page/layout modules and shared branding, so a short design records the common rendering and placement choices.

`RoleSelection` currently vertically centers all content in a narrow column. `AdminLayout` supplies the reusable navbar for trucks, sites, and site details; its existing home link wraps `VipTopLogo`, and its menu collapses below 640px. `ResidentRequestContent` has a separate early-return success screen and a common pre-success main element. The existing specs require VipTop leaf branding and complete replacement of request content on success; both are preserved.

The resident source title (`Prašyti šiukšlių išvežimo`) differs from the durable spec's title (`Siųsti šiukšlių išvežimo prašymą`). This is a pre-existing discrepancy unrelated to logo placement; this change introduces no title requirement or title edit.

## Goals / Non-Goals

**Goals:** Share one bundled image and rendering component across the three placements; keep alignment and size adjustable through Tailwind classes; reserve image dimensions to prevent layout movement.

**Non-Goals:** Replacing VipTop identity, extracting a new navbar architecture, redesigning the form or its confirmation, changing copy, introducing theme variants, or changing API/data contracts.

## Decisions

### Bundle the supplied WebP without editing its artwork

Copy `/home/stitas/Downloads/Logo_of_Vilnius.svg.webp` to `frontend/src/assets/vilnius-logo.webp` during apply. It is already a transparent 960x960 RGBA WebP. Import it through Vite so both development and packaged builds resolve it correctly. An external image URL would add an availability dependency; tracing or converting the artwork would add work and could change the supplied identity.

### Add a small shared VilniusLogo component

Create `frontend/src/components/vilnius-logo.tsx` with the imported asset, `alt="Vilniaus logotipas"`, intrinsic width/height of 960, and class-based sizing. Keep it a plain image component rather than a generalized branding system. Three direct image declarations would duplicate the source and accessibility defaults; modifying `VipTopLogo` would combine two independent identities and make the resident placement awkward.

Use approximately 96px height on public pages and 40px in the navbar, preserving proportions with a bounded width and contain sizing. These are proposed visual defaults, not exact-pixel acceptance criteria. Render the full transparent image, including its original whitespace.

### Place the images in the existing route components

- In `RoleSelection`, use a full-height outer column with the Vilnius logo centered in a top section and the existing role-selection block centered in the remaining space. Keep layout in normal flow so short screens can scroll without overlap. Simply prepending the logo to the existing `justify-center` group would place it near the middle instead of near the page top.
- In `AdminLayout`, retain the VipTop home link on the left and place the compact Vilnius logo in its own home link at the far right. Give each link a Lithuanian accessible name identifying its brand and the home action. Keep the mobile toggle immediately before the city logo, with the expanded menu on a full-width row beneath them. Use flex ordering and desktop auto margin to retain right alignment in both menu states. Preserve the existing menu state, focus, and keyboard handling at 320px width.
- In the common pre-success `ResidentRequestContent` main element, add a centered image wrapper above the heading. This automatically covers loading, missing, failed lookup, ready, and pending submission states. Leave the success early return intact so it continues replacing all prior content.

Avoid absolute positioning: normal flow prevents collision with titles and interactive controls. No shared backend or API contracts change; only the three frontend consumers use the new image component.

## Risks / Trade-offs

- Small navbar artwork may be hard to recognize because the source includes transparent margins -> inspect the full logo at desktop and 320px, tune its bounded size and surrounding gap while keeping the full artwork.
- The extra public-page height can push content down on short phones -> use normal-flow layout, retain safe-area spacing, and verify actions remain reachable by scrolling.
- A developer Downloads path is unavailable on other machines -> copy the image into the repository during apply before importing it, and verify its packaged build URL.

## Migration Plan

No data migration is required. Apply the asset and frontend changes together, run the existing frontend build and lint commands, and visually verify all placements. Preview the packaged build to confirm the asset loads on direct routes. Frontend rollback consists of reverting the asset, component, and three placement edits together.
