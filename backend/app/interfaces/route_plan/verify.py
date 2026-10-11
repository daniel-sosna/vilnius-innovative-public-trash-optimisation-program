"""Check the invariants of a stored route plan against the collection plan and the fleet."""

import argparse
import logging
import sys
from collections import Counter

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.infrastructure.database import create_database_engine
from app.interfaces.route_plan.cli import iso_date
from app.services.collection_plan import get_plan
from app.services.route_plan import get_stored_plan

logger = logging.getLogger(__name__)
TOLERANCE_KM = 0.01


def check(plan: dict, stops: list[dict] | None) -> list[str]:
    """Return the violated invariants; `stops` is the collection plan, or None to skip that check."""
    problems = []
    summary = plan["summary"]
    visits = Counter()
    trips = km = used = served = 0
    for truck in plan["trucks"]:
        if truck["trips"]:
            used += 1
        for trip in truck["trips"]:
            trips += 1
            km += trip["distance_km"]
            load = sum(s["load_m3"] for s in trip["stops"])
            if load > truck["max_volume_m3"] + 1e-6:
                problems.append(f"{truck['name']}: trip load {load:.3f} m3 exceeds capacity {truck['max_volume_m3']}")
            if abs(load - trip["load_m3"]) > 0.002:
                problems.append(f"{truck['name']}: trip load {trip['load_m3']} differs from its stops' sum {load:.3f}")
            for stop in trip["stops"]:
                served += 1
                visits[stop["site_id"]] += 1
    duplicates = [site for site, n in visits.items() if n > 1]
    if duplicates:
        problems.append(f"sites visited more than once: {duplicates[:5]}")
    unserved = {s["site_id"] for s in plan["unserved"]}
    if unserved & set(visits):
        problems.append("a stop is both planned and unserved")
    if stops is not None:
        due = {s["site_id"] for s in stops}
        missing = due - set(visits) - unserved
        if missing:
            problems.append(f"{len(missing)} due stops are neither planned nor unserved")
    opt = summary["optimised"]
    if abs(opt["distance_km"] - km) > TOLERANCE_KM * max(1, trips):
        problems.append(f"summary distance {opt['distance_km']} km differs from the trips' sum {km:.3f}")
    if (opt["trips"], opt["trucks_used"], opt["stops_served"]) != (trips, used, served):
        problems.append("summary trips / trucks used / stops served differ from the stored routes")
    if abs(summary["saved_km"] - (summary["baseline"]["distance_km"] - opt["distance_km"])) > 0.01:
        problems.append("saved km is not baseline minus optimised")
    if summary["baseline"]["stops_served"] != opt["stops_served"]:
        problems.append("baseline and optimised plans serve a different number of stops")
    return problems


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")
    parser = argparse.ArgumentParser(description="Verify the stored route plan of a carrier and date.")
    parser.add_argument("--carrier", required=True)
    parser.add_argument("--date", type=iso_date, required=True, help="Plan date, YYYY-MM-DD")
    try:
        args = parser.parse_args()
    except SystemExit as error:
        return 0 if error.code == 0 else 1
    engine = create_database_engine(Settings())
    try:
        with Session(engine) as session:
            plan = get_stored_plan(session, args.date, args.carrier)
            if plan is None:
                logger.error("no route plan is stored for %s on %s", args.carrier, args.date)
                return 1
            stops = get_plan(session, args.date, [args.carrier])[args.carrier]
        problems = check(plan, stops or None)
        if not stops:
            logger.warning("the collection plan of the date has no stops of the carrier; coverage was not checked")
        if problems:
            for problem in problems:
                logger.error("FAILED: %s", problem)
            return 1
        logger.info("OK: %s on %s: every due stop is planned or reported unserved, trip loads fit, summary matches", args.carrier, args.date)
        return 0
    except Exception as error:
        logger.error("Verification failed: %s", error)
        return 1
    finally:
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
