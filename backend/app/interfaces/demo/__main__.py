"""Repeatable, read-only demo verification: python -m app.interfaces.demo."""
import argparse
import json
import sys
from time import perf_counter

from pydantic import ValidationError

from app.core.config import Settings
from app.infrastructure.database import create_database_engine, create_session_factory
from app.interfaces.demo.schemas import PredictionRequest
from app.services.demo_prediction import DemoError, predict
from app.services.demo_prerequisites import DemoPrerequisiteError
from app.services.demo_navigation import navigate


def main() -> int:
    parser = argparse.ArgumentParser(description="Run real CSV inference without writing model, source or collection-plan records")
    parser.add_argument("--date", required=True, help="September 2026 YYYY-MM-DD input day")
    parser.add_argument("--navigation", action="store_true", help="Also calculate road routes and check assignment coverage")
    args = parser.parse_args()
    try:
        body = PredictionRequest(project_date=args.date)
    except ValidationError:
        print("Invalid date: use a September 2026 YYYY-MM-DD day", file=sys.stderr)
        return 2
    engine = None
    start = perf_counter()
    try:
        engine = create_database_engine(Settings())
        sessions = create_session_factory(engine)
        result = predict(body.project_date, sessions)
        summary = {
            "project_date": result.project_date, "forecast_date": result.forecast_date,
            "evaluated_count": result.evaluated_count, "due_count": result.due_count,
            "mappable_count": result.due_count - result.unmappable_count,
            "unmappable_count": result.unmappable_count,
            "duration_seconds": round(perf_counter() - start, 2),
        }
        if args.navigation:
            ids = [item.bin_id for item in result.bins if item.latitude is not None and item.longitude is not None]
            if not ids:
                summary["navigation"] = "No mappable due bins; navigation skipped"
            else:
                navigation = navigate(result.forecast_date, ids, sessions, {item.bin_id: item.fill_level for item in result.bins if item.latitude is not None and item.longitude is not None})
                assigned = [bin_id for route in navigation.routes for stop in route.stops for bin_id in stop.bin_ids]
                unserved = [bin_id for stop in navigation.unserved for bin_id in stop.bin_ids]
                if len(assigned + unserved) != len(ids) or set(assigned + unserved) != set(ids):
                    raise ValueError("Navigation coverage failed")
                summary["navigation"] = {
                    "source": navigation.source, "assigned_trucks": len(navigation.routes),
                    "stops": sum(len(route.stops) for route in navigation.routes),
                    "assigned_bins": len(assigned), "unserved_bins": len(unserved), "coverage": "assigned or unserved exactly once",
                }
        summary["duration_seconds"] = round(perf_counter() - start, 2)
        print(json.dumps(summary, ensure_ascii=False))
        return 0
    except Exception as error:
        # No credentials or database driver traces in command output.
        message = str(error) if isinstance(error, (DemoError, DemoPrerequisiteError)) else "Verify configured input paths, dependencies and database."
        print(f"Demo check failed ({type(error).__name__}): {message}", file=sys.stderr)
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
