## Context

The current CSV contains 23,777,720 bin-days over 2023-10-10..2026-10-09, with 17 existing columns. Population and registry attributes are snapshots; service outcomes were already simulated from an October schedule. The supplied rules use Lithuanian field names and assume homogeneous sites. Actual sites mix categories, and some bins have unknown categories, zero capacity or unresolved districts. The user approved retaining these rows with both outputs NULL and reporting exclusions.

## Goals / Non-Goals

Generate and inspect two English-named synthetic columns, preserve the source CSV, and publish minimally adapted rules with a complete change log. Deliver reproducible scripts, requested tests, charts and a candid report. No database migration, model training, synchronization, service or UI changes.

## Decisions

1. Use an offline Python CLI and stream complete bin blocks from the existing CSV. Cache shared site/stream daily inflow arrays; keep the original 17 strings when writing. Write to a temporary output and rename only after successful completion. This handles the three-year export without a new database or service.
2. Use `resident_factor` directly for residential bins. For valid non-residential bins, distribute 100 equivalent users per physical site and waste stream in proportion to capacity, across categories. Define D_i=N_i H_i T_i and Q=(q/1000) sum(D) G S W h E Z; allocate A_i=Q D_i B_i/sum(D B). This reduces to the original capacity-weighted formula for homogeneous sites while conserving total inflow and preserving zero exposure. Invalid bins are excluded from generation pools and explicitly audited.
3. Map only reviewed district aliases. Broad municipality values remain unresolved. Contradictory canonical districts at a site invalidate that site's bins rather than choosing an address-derived district. Events are disabled because no event feed exists. Public holidays are derived from the row date, not the cumulative holiday feature.
4. Treat supplied successful synthetic service statuses as assessable visits. Start with unknown state; the first success only anchors the residual. Use latent pre-emptying fill for QR intensity and an independent adjacent-class error for worker assessments. Failed and missed visits neither reset state nor receive an invented assessment.
5. Use stable SHA-256-derived random streams for site propensity, site/stream heterogeneity and daily gamma variation, bin heterogeneity, residuals, worker error and QR reports. Full-range ordered vectors are keyed by seed, identifiers and date range; processing order and chunking of whole bins do not change results. Different ranges are distinct reproducibility configurations. Paired scenarios reuse the same underlying draws, including Poisson inverse-CDF uniforms.
6. Keep internal latent states and report increments in separate diagnostics, never as extra training columns. Validate the full file and run sensitivity scenarios on deterministically selected complete site/stream cohorts, retaining their whole allocation pools. Clearly report the sample and retain all numerical defaults even if results look undesirable.

## Risks / Trade-offs

- Population estimates of zero and extreme catchments can produce many empty or overflowing bins. Preserve these assumptions and expose their consequences rather than tuning class balance.
- Emptying schedules do not establish actual fill generation. Internal checks cannot substitute for measured fill observations; all available historical fill values are NULL.
- The 240 kg/person/year reference is regional and lacks a justified bulk density. Report mass comparison as unavailable; do not invent a conversion.
- Full CSV generation and independent preservation checks take several minutes and several GB. Use streaming and atomic publication; retain the source file and git-ignore generated data.
- Randomness is reproducible within recorded software versions. A different NumPy/SciPy version or date-range configuration may change draws.

## Validation and Delivery

Use unit and statistical tests for thresholds, conservation, shared fallback, masking, lagged recurrence, stochastic moments and independent random streams. Generate the full enriched CSV, independently verify every original field and new-field domain, and create distribution and trajectory plots plus paired rate/calendar/type/QR/district sensitivity checks. Render and visually inspect the English rules PDF. Record every textual rule change and preserve the original supplied rule files.
