"""Build a truck's Driver route from the stored plans and check its invariants."""

import argparse
import logging
import sys

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.infrastructure.database import create_database_engine
from app.services.driver_route import DRIVER_PLAN_DATE, DriverRouteError, build_route

logger = logging.getLogger(__name__)


def check(route: dict) -> list[str]:
    """Return the violated invariants of a built route."""
    problems = []
    if not route["stops"]:
        return problems
    path_size = len(route["path"])
    indexes = [stop["path_index"] for stop in route["stops"]]
    if path_size < 2:
        problems.append("the road path has fewer than two points")
    if any(not 0 <= i < path_size for i in indexes) or any(b <= a for a, b in zip(indexes, indexes[1:])):
        problems.append("stop positions are not strictly increasing within the path")
    if indexes and indexes[-1] != path_size - 1:
        problems.append("the last stop is not at the end of the path")
    ids = [b["bin_id"] for stop in route["stops"] for b in stop["bins"]]
    if len(ids) != len(set(ids)):
        problems.append("a bin appears in more than one stop")
    if any(not stop["bins"] for stop in route["stops"]):
        problems.append("a stop has no bins")
    return problems


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")
    parser = argparse.ArgumentParser(description="Check the Driver route of a truck.")
    parser.add_argument("--truck-id", type=int, required=True)
    try:
        args = parser.parse_args()
    except SystemExit as error:
        return 0 if error.code == 0 else 1
    engine = create_database_engine(Settings())
    try:
        with Session(engine) as session:
            route = build_route(session, args.truck_id)
    except DriverRouteError as error:
        logger.error("%s: %s", error.code, error)
        return 1
    except Exception as error:
        logger.error("Check failed: %s", type(error).__name__)
        return 1
    finally:
        engine.dispose()
    problems = check(route)
    if problems:
        for problem in problems:
            logger.error("FAILED: %s", problem)
        return 1
    stops = route["stops"]
    logger.info(
        "OK: truck %s, plan date %s: %d stops, bins per stop %s, path of %d points",
        args.truck_id, DRIVER_PLAN_DATE, len(stops), [len(s["bins"]) for s in stops], len(route["path"]),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
