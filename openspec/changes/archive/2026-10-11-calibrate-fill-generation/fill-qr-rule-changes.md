# Rule changes: v3.0 to v4.0

The user approved only a bell-shaped worker-assessment scenario and bounded fullness. All artifacts are English. These are synthetic assumptions, not evidence that real bin fullness is normally distributed.

1. **Assessment shape:** replace the prohibition on global calibration with approximate worker class shares 10/20/40/20/10. The five ordinal classes have a bell-shaped histogram; continuous normality is not asserted. No exact row quotas or per-bin balancing.
2. **Fullness meaning and upper bound:** replace F=100 L/V with a monotone response bounded to 0-120%. Exactly 100% is still class 3 and >100% remains class 4. The ceiling is an approved scenario choice, not a measured physical limit.
3. **Source-demand accounting:** retain the old inflow/allocation and accumulated-demand recurrence in m³. Store uncapped assigned demand and excess source demand separately in diagnostics. Conservation applies to source demand; nonlinear fullness is not a conserved physical volume or a correction of the population export.
4. **Calibration fit:** use baseline known-state successful visits in the first synthetic year, 2023-10-10..2024-10-09. Invert the unchanged 10% adjacent-worker-error matrix to obtain latent quantile targets. Freeze the pressure knots for subsequent dates and every sensitivity scenario. Fit-period outcomes are not independent validation.
5. **Monotone response:** linearly interpolate normalized response through zero and four pressure quantiles at the existing class boundaries, adjusted for the unchanged mean 1.5% residue. Add a continuous exponential tail approaching 120%. This preserves increasing fullness between successes without independently drawing a new daily level.
6. **Zero exposure and feasibility:** zero new demand retains the sampled 0-3% residue, never fabricated load. If the zero atom makes the requested first latent share infeasible, retain it plus a 0.005 quantile margin, rescale other fit shares and report the feasible expectation. Invalid/tied calibration knots fail explicitly.
7. **Necessary downstream changes:** daily-order wording now computes fullness using the response; validation checks bounds, independently reconstructs every known-day fullness/worker label, and reports calibration-year/later-year class shares and cap frequency. QR parameters are unchanged but generated counts change because the underlying latent class changes.
8. **Current artifacts:** superseded generated rule versions, previews and stale diagnostics are removed after verified replacement. Original exports and the three-year base CSV remain reproducible inputs. A narrow textual delta and invariant checks document the change without retaining obsolete rules as active files.

## Unchanged rules

All original 17 fields and rows; output masks and exclusions; five class thresholds; first-success anchor; success/failure behavior; residual U(0,0.03); 10% adjacent-class worker error; base q rates and stream ratios; residential exposure and genuine zeros; shared non-residential 100-user fallback; all type/district/calendar factors; persistent lognormal and daily Gamma noise; E=1; QR propensity, severity, Poisson, lag and reset; seeds and independent random namespaces; existing sensitivity settings; evidence/source limitations.

Only fill_level and qr_alerts are appended. Full-registry non-NULL ML predictions remain a separate inference requirement; they do not change training-label missingness.
