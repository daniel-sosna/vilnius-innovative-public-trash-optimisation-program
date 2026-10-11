import argparse
import logging
from dataclasses import fields
from datetime import date

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.infrastructure.database import create_database_engine
from app.optimization.routing import Params
from app.services import route_plan

logger = logging.getLogger(__name__)

DEFAULTS = Params()


def iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a YYYY-MM-DD date: {value!r}") from None


def positive(kind):
    def parse(value: str):
        try:
            number = kind(value)
        except ValueError:
            raise argparse.ArgumentTypeError(f"not a number: {value!r}") from None
        if not number > 0 or number == float("inf"):
            raise argparse.ArgumentTypeError(f"must be positive and finite: {value!r}")
        return number

    return parse


def non_negative_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not an integer: {value!r}") from None
    if number < 0:
        raise argparse.ArgumentTypeError(f"must not be negative: {value!r}")
    return number


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")
    engine = None
    try:
        parser = argparse.ArgumentParser(
            description="Replace the route plan of one carrier and date: for each available "
            "truck of the carrier with a landfill, ordered trips from its landfill that serve "
            "every due stop of the stored collection plan, compared with a nearest-neighbour "
            "baseline. Distances are straight-line estimates times a detour factor."
        )
        parser.add_argument("--carrier", required=True, help="Waste carrier, as in the collection plan")
        parser.add_argument(
            "--date", type=iso_date, required=True,
            help="Date of the stored collection plan (the plan date, not 'today'), YYYY-MM-DD",
        )
        parser.add_argument("--speed-kmh", type=positive(float), default=DEFAULTS.speed_kmh)
        parser.add_argument("--detour-factor", type=positive(float), default=DEFAULTS.detour_factor)
        parser.add_argument("--service-min", type=positive(float), default=DEFAULTS.service_min, help="Minutes per stop")
        parser.add_argument("--unload-min", type=positive(float), default=DEFAULTS.unload_min, help="Minutes per unloading")
        parser.add_argument("--shift-min", type=positive(float), default=DEFAULTS.shift_min)
        parser.add_argument(
            "--overtime-penalty", type=positive(float), default=DEFAULTS.overtime_penalty,
            help="Cost of one overtime minute, in km of driving",
        )
        parser.add_argument("--max-iterations", type=positive(int), default=DEFAULTS.max_iterations)
        parser.add_argument("--seed", type=non_negative_int, default=DEFAULTS.seed)
        try:
            args = parser.parse_args()
        except SystemExit as error:
            return 0 if error.code == 0 else 1
        params = Params(
            speed_kmh=args.speed_kmh,
            detour_factor=args.detour_factor,
            service_min=args.service_min,
            unload_min=args.unload_min,
            shift_min=args.shift_min,
            overtime_penalty=args.overtime_penalty,
            max_iterations=args.max_iterations,
            seed=args.seed,
        )
        engine = create_database_engine(Settings())
        logger.info("planning routes of %s for %s; this takes about a minute", args.carrier, args.date)
        with Session(engine) as session:
            summary = route_plan.compute_plan(session, args.date, args.carrier, params)
        optimised, baseline = summary["optimised"], summary["baseline"]
        logger.info(
            "route plan stored for %s on %s: stops=%d, served=%d, unserved=%d, trucks excluded (no landfill)=%d",
            args.carrier, args.date, summary["stops_total"], optimised["stops_served"],
            summary["unserved_stops"], summary["excluded_trucks"],
        )
        logger.info(
            "parameters (assumptions): %s",
            ", ".join(f"{f.name}={getattr(params, f.name)}" for f in fields(params)),
        )
        for name, figures in (("optimised", optimised), ("baseline (nearest neighbour)", baseline)):
            logger.info(
                "%s: distance=%.1f km (estimate, straight-line x detour), trips=%d, trucks used=%d, overtime=%.0f min",
                name, figures["distance_km"], figures["trips"], figures["trucks_used"], figures["overtime_min"],
            )
        logger.info(
            "saved vs baseline: %.1f km (%.1f%%); solver iterations=%d, solve time=%.1f s",
            summary["saved_km"], summary["saved_percent"], summary["iterations"], summary["solve_seconds"],
        )
        if summary["stopped_by_wall_limit"]:
            logger.warning("the solver stopped at its wall-clock limit; the result may differ between machines")
        return 0
    except route_plan.NoCollectionPlan:
        logger.error("Route plan failed: the collection plan must be built first for this date; nothing was changed")
        return 1
    except route_plan.NothingToPlan:
        logger.error("Route plan failed: the carrier has no due stops on this date, nothing to plan; nothing was changed")
        return 1
    except route_plan.NoEligibleTruck:
        logger.error(
            "Route plan failed: the carrier has no available, non-deleted truck with a landfill; nothing was changed"
        )
        return 1
    except Exception as error:
        cause = getattr(error, "orig", error)
        reason = f"{type(cause).__name__}: {cause}" if isinstance(error, SQLAlchemyError) else str(error)
        logger.error("Route plan failed, nothing was changed: %s", reason)
        return 1
    finally:
        if engine is not None:
            engine.dispose()
