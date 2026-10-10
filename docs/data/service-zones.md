# Service zones

`service_zones` holds the waste-collection service-zone polygons shown on the map analytics page. Behaviour is specified in [`service-zone-import`](../../openspec/specs/service-zone-import/spec.md).

Put the zone GeoJSON in the [data directory](../development.md#data-directory) as `service_zones.geojson`. The supplied file is called `serv_zones.geojson`, so copy it under the canonical name. The [CSV import](import.md#geojson-sources) loads it automatically. To load only the zones, run:

```bash
docker compose exec backend uv run python -m app.interfaces.service_zones [--file PATH]
```

- `--file` defaults to `service_zones.geojson` in the data directory.
- The whole FeatureCollection is validated, then only `service_zones` is replaced, in one transaction. `ZONA` becomes `zone_name`, `ZONOS_NR` becomes the integer `zone_number`, and every Polygon ring is kept.
- Standard longitude/latitude GeoJSON and the supplied CRS84 declaration are accepted. Re-importing creates no duplicates, and a valid empty collection clears the table.
- The command exits 0 on success and prints the row count. It exits 1 on missing or invalid input or a database error, and keeps the stored zones.
