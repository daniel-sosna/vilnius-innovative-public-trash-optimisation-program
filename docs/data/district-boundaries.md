# District boundaries (Seniūnijos)

`district_boundaries` holds the Vilnius district (seniūnija) polygons shown on the map analytics page. Behaviour is specified in [`district-boundaries`](../../openspec/specs/district-boundaries/spec.md).

Put `vilnius_seniuniju_ribos.geojson` in the [data directory](../development.md#data-directory). The [CSV import](import.md#geojson-sources) loads it automatically. To load only the boundaries, run:

```bash
docker compose exec backend uv run python -m app.interfaces.district_boundaries [--file PATH]
```

- `--file` defaults to `vilnius_seniuniju_ribos.geojson` in the data directory.
- The whole FeatureCollection is validated, then the catalog is replaced in one transaction. Source names, diacritics, coordinates and all Polygon rings are kept.
- Duplicate names or `OBJECTID`s, a CRS other than longitude/latitude, non-finite positions, and unclosed or degenerate rings are rejected. These checks are structural, not a full topology validation, and nothing is reprojected.
- Re-importing replaces the rows, and the generated IDs can change. Other tables are untouched.
- The command exits 0 on success and prints the district count. It exits 1 on missing or invalid input or a database error, and keeps the previous catalog.
- The supplied snapshot has 21 districts. Its effective date is unknown.

## API check

`district_boundaries.check` compares the API response with the database (every ID, name and ring) and prints counts, payload size and timing. It exits 1 on any mismatch or read failure.

```bash
docker compose exec -T backend uv run python -m app.interfaces.district_boundaries.check \
  --url http://backend:8000/map-analytics/district-boundaries \
  --url http://frontend:5173/api/map-analytics/district-boundaries --host localhost
```

Repeat `--url` once for each endpoint. `--host` sets the HTTP `Host` header for the Vite proxy.
