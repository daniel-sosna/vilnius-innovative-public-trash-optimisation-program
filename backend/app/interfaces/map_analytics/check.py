"""Read-only comparison of population HTTP responses with the configured database.

Run with ``python -m app.interfaces.map_analytics.check --url <endpoint>``.
This is a manual verification command, not an automated test suite.
"""

import argparse
import json
import sys
from time import perf_counter
from urllib.request import Request, urlopen

from sqlalchemy import text

from app.core.config import Settings
from app.infrastructure.database import create_database_engine


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", action="append", help="Full endpoint URL; repeat for backend and proxy")
    parser.add_argument("--host", help="Optional HTTP Host header for a development proxy")
    args = parser.parse_args()
    engine = None
    try:
        engine = create_database_engine(Settings())
        with engine.connect() as connection:
            connection.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
            connection.execute(text("SET LOCAL statement_timeout = '5s'"))
            rows = connection.execute(text(
                "SELECT id, geometry, density_per_ha, suppressed, area_ha, residents "
                "FROM population_cells ORDER BY id"
            )).mappings().all()
            for url in args.url or ["http://127.0.0.1:8000/map-analytics/population-cells"]:
                started = perf_counter()
                request = Request(url, headers={"Host": args.host} if args.host else {})
                with urlopen(request, timeout=30) as response:
                    payload = response.read()
                elapsed = perf_counter() - started
                data = json.loads(payload)
                if set(data) != {"type", "features"} or data["type"] != "FeatureCollection":
                    raise ValueError("Expected a GeoJSON FeatureCollection")
                features = data["features"]
                if [f["id"] for f in features] != [row["id"] for row in rows]:
                    raise ValueError("Feature IDs must exactly match ordered, unique stored IDs")
                for row, feature in zip(rows, features, strict=True):
                    expected = {key: row[key] for key in ("density_per_ha", "suppressed", "area_ha", "residents")}
                    if row["density_per_ha"] is None and not row["suppressed"]:
                        expected["residents"] = None
                    if set(feature) != {"type", "id", "geometry", "properties"} or feature["type"] != "Feature":
                        raise ValueError(f"Invalid feature envelope at ID {row['id']}")
                    if feature["geometry"] != {"type": "Polygon", "coordinates": row["geometry"]}:
                        raise ValueError(f"Geometry differs at ID {row['id']}")
                    props = feature["properties"]
                    if props != expected or type(props["suppressed"]) is not bool:
                        raise ValueError(f"Properties differ at ID {row['id']}")
                    for key in ("density_per_ha", "area_ha", "residents"):
                        if props[key] is not None and type(props[key]) not in (int, float):
                            raise ValueError(f"Non-numeric {key} at ID {row['id']}")
                print(f"PASS {url}: {len(features):,} polygons; {len(payload):,} bytes; {elapsed:.3f}s; all IDs, rings and properties match")
            numeric = sum(row["density_per_ha"] is not None for row in rows)
            suppressed = sum(row["suppressed"] for row in rows)
            print(f"Source states: {numeric} numeric, {suppressed} suppressed, {len(rows) - numeric - suppressed} missing; read-only snapshot")
        return 0
    except Exception as error:
        # Avoid printing configuration or SQL that could contain credentials.
        print(f"FAIL: {type(error).__name__}: population response verification failed", file=sys.stderr)
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
