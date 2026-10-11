# Design

## Context

See [proposal.md](proposal.md) for motivation and the delta specs for observable behavior.

- `app.interfaces.bin_population.allocation` already parses the source polygons, defines residential groups, groups bins by exact coordinates/waste type, projects local ground distances and allocates each polygon's residents to its nearest point. Its outputs omit a direct area-to-point mapping; expose that mapping through a backward-compatible pure calculation helper without changing existing allocation semantics or database tables.
- The configured data directory contains registry exports, population geometry and an immutable enriched CSV. The retention record identifies a daily source interval of 2026-06-01 through 2026-10-09 for 21,695 eligible bins. Confirm row-level coverage during generation; the filename's earlier start is not authoritative.
- Source `bin_hist` has only one month of real attempts and no measured fill labels. The enriched source's `fill_level` and collection outcomes are synthetic. This feature consumes the fill assessments and does not use `was_serviced` as an overflow label.
- The map has five registered datasets, a stable MapLibre instance and a shared card below it. `createPolygonLayer` supports area rendering/details but has no `setData`; `useLayerSession` caches by fixed layer ID. `AnalyticsCanvas` recreates the map if the definitions array identity changes. These are concrete integration points for monthly data replacement.
- There is no shared selected-today state in the frontend/backend. Offline prediction's `--today` is a separate input, not an application clock.

## Goals / Non-Goals

**Goals:** Keep calculation reproducible and offline-capable, publish portable results, preserve completed analyses, and integrate one parameterized layer into the current map without changing camera or unrelated dataset behavior.

**Non-Goals:** New infrastructure, forecasts, a second fill model, service-failure analysis, resident demand inferred from footfall, or implementing a global date mechanism. No automated test suite is added; repeatable verification commands and manual UI evidence cover the slice.

## Decisions

### 1. Use existing population polygons as analysis areas

Retain original geometry, holes and `OBJECTID` as area identity. Emit one feature per area/waste type, with stable numeric identity `OBJECTID * 10 + waste_type_code` for codes 1–3. Do not merge areas into mutable hotspot outlines. Unknown-density geometry is retained with unavailable metrics but not visibly filled; known zero-demand areas are neutral and do not claim shortage.

The earlier 250 m grid was an illustrative option, not a required boundary. Existing polygons avoid new intersection libraries, preserve source population totals and match the established map renderer. Merged source polygons are not all 1 ha and are described as source areas, not uniform squares. Administrative/service boundaries remain context layers.

### 2. Attribute access and capacity through the existing catchment model

For each waste type independently, let `s(c,w)` be the closest eligible point to population area `c` using the existing centroid, local projection and tie-breaking behavior. A point is the existing exact-coordinate/waste-type group of residential bins with positive capacity; identify it by its minimum bin ID, not address-based `site_id`.

```
P_c       = source density * actual polygon area (record suppression assumption)
R_sw      = sum P_c over areas assigned to point s for waste type w
C_sw      = sum positive capacity of the eligible bins at that point
L_sw      = R_sw / C_sw
C_cw      = C_sw * P_c / R_sw, when R_sw > 0
d_cw      = distance from the source polygon centroid to point s
```

An area's pressure is `L_sw`; its attributed capacity is `C_cw`. This avoids the boundary error of dividing area residents by containers physically inside the polygon. It also conserves resident demand and shared capacity per waste type. Points serving no residents remain in quality diagnostics, not an invented shortage result. Unknown population does not become zero; an absent point has `distance=null`, `pressure=null`, attributed capacity zero and an explicit service-gap flag.

Freeze pressure references from the registry/population snapshot: the unweighted 80th percentile of positive-demand point pressures for each waste type. Proposed starting policy defaults are pressure at or above that threshold or access distance over 300 m. These are operational screening parameters, not municipal standards. Store their numeric values and reference fingerprint in every artifact, expose flags separately and compare sensitivity before delivery. Never calculate thresholds from the viewport or re-normalize them for each month.

### 3. Model level-4 assessments at the serving point

Stream the enriched CSV once for requested months. Validate unique `(bin_id,date)` keys, domain 0–4 or NULL, registry membership and copied static attributes. Preserve all daily rows for coverage checks, but count only non-NULL fill assessments for statistics. Aggregate by serving point, waste type and month, using residential eligible bins only:

```
N_sw,m = number of known fill assessments
Y_sw,m = number of those assessments equal to 4
raw_sw,m = Y_sw,m / N_sw,m, if N_sw,m > 0
```

Also retain distinct assessed days, registered point-bin count, assessed-bin count and assessed-bin fraction. The fraction concerns assessed bin-days, not days continuously overflowing. Level 3 is excluded from `Y`.

Use one empirical-Bayes beta-binomial smoother for each waste type and analyzed period. Fit positive `alpha,beta` by deterministic bounded marginal-likelihood optimization across points with `N>0`; use parameters `mu=alpha/(alpha+beta)` and concentration `k=alpha+beta`, bounds `mu in [1e-6,1-1e-6]`, `k in [0.1,1000]`, and fixed initialization from the pooled rate and `k=10`. Record convergence, parameters and point counts. Failed fitting fails publication for that month, rather than silently switching methods. A type with no assessments has unavailable fill estimates and no fitted prior.

For assessed points, the posterior is `Beta(Y+alpha,N-Y+beta)`. Save its mean, central 90% interval and probability that the point's rate exceeds `mu + 0.05` (probability zero when the cutoff is at least one). Proposed initial sufficient-evidence defaults: at least five assessments, three assessed dates and 50% of point bins assessed. Flag elevated fill evidence when these are satisfied and exceedance probability is at least 0.90. These policy defaults are versioned and configurable; interval precision is conditional on this model, not a guarantee of independent real-world events.

Each area references its point's statistics; it does not fit another model. Many areas can share the same evidence. City summaries deduplicate by point/type; counts and confidence are not multiplied by the number of map polygons. Model fitting uses only records within the result period, including the cutoff for eventual partial-month analysis.

Alternatives: raw fractions are too unstable at sparse points; a new classifier is unnecessary for descriptive monthly analysis; combining signals in an arbitrary weighted score would obscure explanations. This model is separate from, and does not replace, the existing fill predictor.

### 4. Keep classification transparent

Evaluate structural availability first, then evidence sufficiency, then pressure and elevated fill flags:

| Code | Meaning |
|---|---|
| `unavailable` | Unknown demand, no serving point or no resident demand; reason distinguishes them |
| `insufficient_evidence` | Structural metrics available, but fill evidence insufficient; pressure/access flags remain visible |
| `priority_shortage` | Elevated pressure/access and elevated level-4 evidence |
| `potential_shortage` | Elevated pressure/access without elevated level-4 evidence, with sufficient assessments |
| `overflow_without_pressure` | Elevated level-4 evidence without elevated pressure/access |
| `ordinary` | Neither elevated component with sufficient assessments |

Conclusions are deterministic Lithuanian text from reason codes and numbers. They identify candidate actions (check capacity, placement or frequency) and avoid claiming causal diagnosis. The same six categories retain the same colors for all months. Detailed provenance and assumptions remain in the portable artifact; popups show only seven short metric rows and one conclusion, without synthetic-data notices.

### 5. Publish one portable GeoJSON per completed month

Add an explicit `python -m app.interfaces.container_adequacy` command, with `--month YYYY-MM` or `--all-complete`, explicit source overrides, policy options and `--regenerate` for an existing result with changed inputs. Resolve default exports through `data_dir()` and the existing highest-numeric-suffix rule. The enriched CSV is an explicit configured input; never choose a base CSV or regenerate labels implicitly.

Keep mathematical processing in a pure service module; retain only the CLI/validation boundary under `interfaces`. Reuse existing allocation code. Put SciPy, used for beta functions, quantiles and fitting, in an optional backend `analytics` dependency group. Serving saved artifacts must not import SciPy or require the analysis extras. Document native installation and `uv run --extra analytics` invocation; no separate deployment is introduced.

Check the three mandatory registry/history exports and population file before reading collection data. History is a required project development export, not an input for level-4 labels. Validate declared cohort and actual bin-day coverage; report excluded registry bins explicitly. With the retained source, initially generate June–September only. Empty labels do not make a complete daily calendar incomplete; missing calendar days/cohort rows do. Use CLI date arguments and source coverage, not the machine's wall clock, to determine eligible periods.

Write to `<data_dir>/analyses/container-adequacy/adequacy_YYYY-MM.geojson`. Each file contains:

- Standard `FeatureCollection` geometry plus top-level `analysis` metadata: stable ID, schema/method versions, month/start/end, `complete`, source hashes and kinds, cohort/quality summary, pressure reference, fitted per-type parameters, policy settings and assumptions.
- Features with `population_cell_id`, `waste_type`, serving-point ID, estimated residents, suppression/unknown flags, attributed capacity, point capacity/residents/bin count, pressure and distance, raw counts/frequency, coverage, posterior metrics, category and reason codes. Nullable values are JSON null; numeric outputs must be finite. No raw private source text is needed.
- Sorted feature order and canonical JSON for reproducibility. The file-content SHA-256 is the catalog revision and is not recursively stored inside the hashed file. A semantic input/method fingerprint is stored separately in metadata.

Write and validate a temporary file in the same directory, then atomically replace the target. Ignore temporary files in discovery. An identical existing fingerprint is reused unchanged; a mismatch without `--regenerate` fails with an actionable message. Batch generation is atomic per month: already completed months remain valid if another month fails. Report every succeeded, reused and failed month; return a nonzero exit code if any requested month fails. Source hashes before/after verification demonstrate immutability.

GeoJSON is the reproducible transfer artifact. Explicit import publishes it to PostgreSQL, matching the existing service-zone/district import lifecycle. A single `container_adequacy_analyses` row stores one complete collection: `id`, file-SHA256 `revision`, `type`, `analysis` JSONB and `features` JSONB. Keeping all features together preserves atomic monthly replacement and rich metadata without additional joins or PostGIS.

### 6. Import and serve through the existing database lifecycle

Add migration 0017 and the matching ORM model. `python -m app.interfaces.container_adequacy_import --file <path>` accepts repeated files; `--all` selects completed-month artifacts under the configured output directory. Validate every selected file before opening the write transaction. Reject duplicate analysis IDs, invalid geometry/metrics/metadata and absent inputs. Upsert only selected IDs in one caller-owned transaction; unchanged file revisions are a no-op, unrelated months remain, and any failure rolls the batch back. Imported replacement requires explicit invocation; map reads and catalog refresh never import files.

The existing map routes use `CollectionSession` like all other map layers. The catalog selects only metadata and revision, latest first; retrieval reconstructs the full GeoJSON including all feature properties and metadata, with the imported file hash as ETag. Empty table returns an empty catalog, unknown/bounded IDs return 404, and database failures use existing map read errors. Neither CSVs, generated files nor SciPy are required on the API host after import. No file fallback is used.

### 7. Extend existing layer lifecycle for parameterized data

Keep the `mapLayers` definitions array stable and add one `adequacy` definition. Reuse the current checkbox and adjacent arrow/dialog pattern for month and single waste-type controls. Keep the existing card position and typography; use an existing-style refresh button for catalog discovery. Fetch the catalog on first analysis activation, not on unrelated layer toggles. Select latest month/mixed waste initially and preserve choice in the page session.

Extend loading support narrowly to distinguish logical layer identity from `{analysis_id,revision}` cache identity. Pending reads share that identity. Month/revision changes close only the analysis popup and hide stale geometry until the selected result is ready. Cache all three types in one monthly response; waste-type selection filters it locally. Do not rebuild the definitions array for each catalog/month change, because the current map effect depends on its identity.

Add `setData` support to the existing polygon helper so source data and its feature lookup used by popups change together. Use the same helper for analysis; existing polygon layers retain their behavior. Put analysis fill above population (order 25, between population order 20 and service outlines/names), below points and basemap labels. Add a shared topmost-interactive-polygon guard so population and analysis handlers do not compete for the same click; existing points retain priority.

Legend entries use fixed semantic colors: red priority, amber potential, violet elevated fill without pressure, muted green ordinary, gray insufficient evidence and transparent unknown population. No-serving-point populated areas remain visible with unavailable/service-gap detail. Preserve `N/A`, existing Lithuanian loading/error/retry text, and `lt-LT` numeric formatting. Raw point evidence is explicitly labeled as serving-point data.

### 8. Record selected-today as a deferred integration dependency

The generator's internal period contract is `{month,period_start,period_end,complete}`. Initial public CLI/catalog/UI expose completed months only. No date-change trigger, application clock, date selector, background scheduler or speculative global-state API is implemented by this change.

When the shared selected-today capability is implemented, its change must include this integration as an acceptance condition:

1. Resolve end-of-day selected date in the existing Europe/Vilnius data-day convention.
2. Invoke the same generator for `[month_start,selected_today]`, excluding later outcomes from aggregation and prior fitting. Emit `complete:false` unless the cutoff is the true month end with full source coverage.
3. Publish `adequacy_YYYY-MM_through_YYYY-MM-DD.geojson` with a distinct period ID/revision, preserving all completed files, and import it through the same database publication pipeline. Reject cutoffs beyond available source coverage rather than filling forward.
4. Refresh the catalog, restrict selectable analyses to the shared date, invalidate the selected artifact cache and render the matching result. Use request/generation identity so an old date's late response cannot overwrite the active date.
5. Keep completed-month preservation and explicit-regeneration rules; selecting a later date does not silently rewrite completed files.

This is a future project-integration obligation. Keep it as plain workflow follow-up in tasks so present implementation can finish without claiming the absent shared capability is implemented or creating an indefinitely unfinished tracked task.

## Risks / Trade-offs

- Synthetic fill depends on resident demand and is observed mainly before synthetic successful collections → disclose provenance and selection bias; do not interpret the relationship as independent evidence, overflow duration or real-world accuracy.
- Static registry/population snapshots applied to past months → persist source fingerprints and estimated resident labels; do not claim historical inventory changes.
- Straight-line centroid access ignores walking routes, barriers, private access and merged polygon variation → label estimated distance and nearest eligible residential point; surface long-distance outliers and use sensitivity checks.
- Capacity units are unverified → retain the m³ assumption in metadata; verify source interpretation with the team before claiming a physical deficit.
- Sparse glass assessments and correlated bin/day events → retain coverage and conditional intervals in the artifact and label point evidence in the popup; insufficient data is a result rather than a forced confident class.
- Operational defaults can move categories → record parameters and compare pressure quantiles 75/80/90%, access 200/300/500 m and evidence criteria; do not tune them to produce visually attractive hotspots.
- Repeated polygon geometry for three waste types increases file size → stream CSV aggregation, gzip HTTP responses if already supported, cache by file revision and measure generation/load time; avoid adding tile infrastructure for this MVP.
- Reading an obsolete monthly file can contradict newer source data → preserve it as a snapshot with hashes; explicit regeneration and catalog revision control make replacement deliberate.

## Migration Plan

Implement calculation and file verification, apply Alembic migration 0017, explicitly import completed-month artifacts, then serve the database-backed map. Transfer files with other ignored data files; imports publish them to the target database. Source data regeneration is not needed. Rollback removes imported-analysis table through migration downgrade and hides/removes the added layer and API routes; saved files and original data can remain without affecting current map endpoints.

Deliver a repeatable verification command that checks input/output domains, resident/capacity conservation, unique evidence aggregation, month coverage, category explanations, completed-file reuse, failed-write preservation and catalog schemas. Record actual commands, timings, sensitivity outputs and desktop/320-pixel UI evidence under this change. Update `docs/data/container-adequacy.md` for operation/assumptions and link its specs; add only the corresponding pipeline/features/index rows to README.
