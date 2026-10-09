# Tasks

## 1. Shared asset and entry screen

- [x] 1.1 Copy the supplied `/home/stitas/Downloads/Logo_of_Vilnius.svg.webp` unchanged into `frontend/src/assets/vilnius-logo.webp` and create the shared `VilniusLogo` component with a Lithuanian image description, intrinsic dimensions, and adjustable sizing; verify the copied asset matches the source and the component preserves its full transparent artwork.
- [x] 1.2 Add the shared logo centered near the top of `/`, above a role-selection block centered in the remaining space; verify desktop and 320px layouts show the full logo, VipTop leaf branding, heading, and usable role buttons without overlap or horizontal overflow, and `Administratorius` still opens `/admin/trucks`.
- [x] 1.3 Update the entry/navigation description in `README.md` to describe Vilnius branding alongside VipTop; verify the text matches the implemented placements and retains the existing role and navigation behavior.

## 2. Shared administrator navbar

- [x] 2.1 Place the compact Vilnius logo in its own home link at the far right of `AdminLayout`, retain VipTop branding on the left, and use Lithuanian accessible names for both home actions; verify right alignment on trucks, sites, and site-detail routes and both home actions return to `/`.
- [x] 2.2 Verify the updated navbar at desktop, 640px, and 320px widths: both identities fit, desktop links remain visible at or above 640px, and the mobile toggle, link selection, Escape handling, and focus restoration work with the logo visible in both menu states; adjust spacing or bounded image size as needed.

## 3. Resident-request page

- [x] 3.1 Add the shared logo centered above the heading in the common pre-success resident content; verify ready, loading, failed lookup, missing/invalid bin, pending submission, and failed submission states show it while preserving existing controls and feedback, and success replaces it with the existing confirmation. Use controlled frontend responses or isolated synthetic data for submission checks, without creating reports against real imported bins.
- [x] 3.2 Verify the resident layout at desktop and 320px widths, including a short phone viewport, long field values, and service-information presence/absence; confirm the full logo fits, its Lithuanian description is exposed to assistive technology, and the bottom action remains reachable with safe-area spacing. Update `docs/resident-request-verification.md` with these placement/state checks and record observed results or concrete verification limits.

## 4. Integration verification

- [x] 4.1 Run `npm run build` and `npm run lint` from `frontend/`; resolve any issues introduced by the logo changes and record the command outcomes.
- [x] 4.2 Preview the built frontend and open/refresh `/`, an admin deep link, and `/resident-request/{bin_id}`; verify all three placements load the bundled asset without dependence on the original Downloads path or an external image host, with original artwork and proportions preserved.
