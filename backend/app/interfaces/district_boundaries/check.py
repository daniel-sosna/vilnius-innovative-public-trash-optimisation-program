"""Read-only manual comparison of district HTTP responses and the SQL snapshot."""

import argparse
import json
import sys
from time import perf_counter
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from sqlalchemy import text

from app.core.config import Settings
from app.infrastructure.database import create_database_engine


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", action="append", help="Full endpoint URL; repeat for backend and proxy")
    parser.add_argument("--host", help="Optional HTTP Host header for a development proxy")
    try:
        args = parser.parse_args()
    except SystemExit as error:
        return 0 if error.code == 0 else 1
    engine = None
    try:
        engine = create_database_engine(Settings())
        with engine.connect() as connection:
            connection.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
            connection.execute(text("SET LOCAL statement_timeout = '5s'"))
            rows = connection.execute(text(
                "SELECT id, district_name, geometry FROM district_boundaries ORDER BY id"
            )).mappings().all()
            for url in args.url or ["http://127.0.0.1:8000/map-analytics/district-boundaries"]:
                started = perf_counter()
                request = Request(url, headers={"Host": args.host} if args.host else {})
                with urlopen(request, timeout=30) as response:
                    payload = response.read()
                elapsed = perf_counter() - started
                data = json.loads(payload)
                if set(data) != {"type", "features"} or data["type"] != "FeatureCollection":
                    raise ValueError("Expected a GeoJSON FeatureCollection")
                features = data["features"]
                if not isinstance(features, list) or [f["id"] for f in features] != [r["id"] for r in rows]:
                    raise ValueError("Feature IDs differ from ordered stored IDs")
                for row, feature in zip(rows, features, strict=True):
                    if (set(feature) != {"type", "id", "geometry", "properties"}
                            or feature["type"] != "Feature" or type(feature["id"]) is not int
                            or feature["geometry"] != row["geometry"]
                            or feature["properties"] != {"district_name": row["district_name"]}):
                        raise ValueError("Stored ID/name/rings differ from the response")
                # Report only endpoint paths, never credentials or query parameters.
                path = urlsplit(url).path
                print(f"PASS {path}: {len(features):,} districts; {len(payload):,} bytes; "
                      f"{elapsed:.3f}s; all ordered IDs, names and rings match SQL")
            rings = sum(len(row["geometry"]["coordinates"]) for row in rows)
            positions = sum(len(ring) for row in rows for ring in row["geometry"]["coordinates"])
            print(f"Read-only snapshot: {len(rows)} districts; {rings} rings; {positions:,} positions")
        return 0
    except Exception as error:
        print(f"FAIL: {type(error).__name__}: district response verification failed", file=sys.stderr)
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
