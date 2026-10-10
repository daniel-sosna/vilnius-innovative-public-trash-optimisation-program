# Design

## Context

See proposal.md. The prior generator conserves source demand but calls its unbounded capacity ratio fullness. Approximately 62% of worker assessments are class 0. This change extends the completed, unarchived synthetic-fill-and-qr delta; no main spec for that capability exists yet.

## Goals / Non-Goals

Use one reproducible monotone response, preserving raw source-demand equations and causal daily ordering. The output contract remains 19 columns with nullable labels and QR counts. Model training and all-registry inference are separate work.

## Decisions

1. Retain raw accumulated demand L in m³ and the existing inflow Q/A equations exactly. Represent calibrated fullness separately. Conservation applies to demand, not the nonlinear occupancy response; this is an explicit scenario-model change, not correction of measured capacity or population.
2. Fit four positive demand-pressure quantiles at assessable visits in the first year (2023-10-10..2024-10-09). Solve the existing adjacent-error transition matrix for latent shares that yield expected worker shares 10/20/40/20/10. Use the corresponding cumulative quantiles of new demand since prior successful service; zero demand stays at zero. No future service date enters an individual state calculation. This is synthetic distribution calibration using collection-day sampling, not estimating waste rates from the next visit.
3. Map new demand/capacity pressure monotonically to a normalized response h: h(0)=0, interior knots map to thresholds adjusted for mean 1.5% residue, and a continuous exponential upper tail approaches 1. Fullness is r+(120-r)h, where r is the unchanged cycle residue in [0,3). Thus boundedness, monotonic accumulation, resets and zero exposure hold. Reject insufficient/tied calibration knots explicitly rather than inventing data.
4. Freeze the baseline map for all sensitivities, otherwise recalibration would conceal their effects. QR-only changes retain identical fill and demand. Calibration-year outcomes are not independent validation; report later-year distributions separately. No per-bin/time histogram forcing or changed worker noise.
5. Store calibrated fullness plus raw demand and raw excess-demand volume in diagnostic NPZ arrays; retain only fill_level/qr_alerts in CSV. Save calibration, fit interval, expected/actual shares, zero mass, knots and hashes in manifests. Retain stable seeds, original status/exclusion policies and source columns.
6. Replace results atomically where supported; remove superseded rules/PDF previews and old diagnostics after new outputs pass. Preserve all source/preparation inputs and the three-year base CSV. Keep a narrow textual delta and invariant review rather than retaining obsolete rules as active files. The newly regenerated fixture is a current repeatable check, not a superseded result.

## Risks / Trade-offs

- Assumed class balance is not real evidence: report this explicitly and do not run a normality test on ordinal codes as if they were continuous Gaussian samples.
- Zero exposure and changing service sample mix limit exact matching: publish period/stream distributions and deviations; do not fabricate load.
- Calibration uses first-year synthetic visit sampling: record the fit window and recommend subsequent-year temporal evaluation for downstream models.
- Bounded occupancy can hide bad exposure/capacity assignments: publish uncapped demand volumes and excess-demand totals, and preserve conservation checks.
- Saturation changes marginal effects: freeze the response for paired sensitivities and inspect bounded trajectories and cap frequency.

## Migration Plan

Create updated rules and calibration; update generator/validation and existing requested tests; run fixture; regenerate and independently verify full CSV; rerun with identical parameters to confirm hashes; render/review PDF and charts; delete only explicitly inventoried superseded generated files within backend/data. Leave this change available for review without archiving.
