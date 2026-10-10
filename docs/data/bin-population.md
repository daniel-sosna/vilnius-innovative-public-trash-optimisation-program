# Bin population (residents per bin)

`bin_population` estimates how many residents each bin serves, using the Vilnius population-density grid. Behaviour is specified in [`bin-resident-allocation`](../../openspec/specs/bin-resident-allocation/spec.md).

Put `population_density_1ha.geojson` in the [data directory](../development.md#data-directory), [import](import.md) the collection data, then run:

```bash
docker compose exec backend uv run python -m app.interfaces.bin_population
```

| Option | Default |
|---|---|
| `--file PATH` | `population_density_1ha.geojson` in the data directory |
| `--suppressed-density N` | 5. The assumed residents per ha for the source value `"<11"` (between 0 and 10). |

- The command takes a few seconds. It replaces `population_cells` and `bin_population` in one transaction, so a failure changes nothing.
- It exits 0 on success and 1 on failure.
- The summary prints totals, how many bins lie in a polygon, and for each waste type: residential bins, collection points, allocated and unallocated residents, and distance and factor percentiles (p50, p90, p99, max).

## Output

- `population_cells` has one row per source polygon (`id` = `OBJECTID`), with density per ha, area, `residents` (density × area, with the assumed density applied) and geometry.
- `bin_population` stores, for each bin, `population_cell_id` (the polygon containing the bin, or NULL) and `resident_factor`. The factor is an **estimate** of the residents the bin serves, not an observation. The [bin-day calendar](bin-days.md) copies both columns.

## Assumptions

- Each polygon's residents use the nearest residential collection point of each waste type, measured from the polygon centroid. A collection point is the set of bins of that type at identical coordinates. The point's residents are split among its bins by capacity.
- Residential means object group `Daugiabučiai namai`, `Dvibučiai`, `Daugiabučių/garažų bendrijos`, `Sodų bendrijos` or `Sodų/garažų bendrijos`, with capacity above 0. All other bins get factor 0, and the fill generator supplies their baseline.
- The source value is a density per ha, and merged polygons are allocated whole from their centroid. `"<11"` counts as `--suppressed-density`, and null counts as 0.
- Declared residence is assumed to match actual residence.
- Isolated points can take very large catchments, up to about 7,600 residents for mixed waste. The p99 and max values are printed so outliers are visible.
