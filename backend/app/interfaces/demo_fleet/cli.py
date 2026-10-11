import argparse
import logging
from datetime import date

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.infrastructure.database import create_database_engine
from app.services import demo_fleet

logger = logging.getLogger(__name__)


def iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a YYYY-MM-DD date: {value!r}") from None


def capacity_list(value: str) -> tuple[int, ...]:
    try:
        sizes = tuple(int(part) for part in value.split(","))
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a comma-separated list of integers: {value!r}") from None
    if not sizes or any(size <= 0 for size in sizes):
        raise argparse.ArgumentTypeError(f"capacities must be positive: {value!r}")
    return sizes


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")
    engine = None
    try:
        parser = argparse.ArgumentParser(
            description="Replace the demo trucks (names starting with 'DEMO ') with a fleet "
            "sized from the stored collection plan of --date. The trucks are invented demo "
            "data; other trucks are not touched."
        )
        parser.add_argument(
            "--date", type=iso_date, required=True,
            help="Date of the stored collection plan (the plan date, not 'today'), YYYY-MM-DD",
        )
        parser.add_argument(
            "--capacities", type=capacity_list, default=demo_fleet.DEFAULT_CAPACITIES,
            help="Comma-separated truck sizes in m3 drawn at random "
            f"(default {','.join(map(str, demo_fleet.DEFAULT_CAPACITIES))})",
        )
        parser.add_argument("--shift-minutes", type=int, default=demo_fleet.DEFAULT_SHIFT_MINUTES)
        parser.add_argument(
            "--trip-minutes", type=int, default=demo_fleet.DEFAULT_TRIP_MINUTES,
            help="Assumed length of one trip, only used to size the fleet",
        )
        parser.add_argument("--seed", type=int, default=0)
        try:
            args = parser.parse_args()
        except SystemExit as error:
            return 0 if error.code == 0 else 1
        if args.shift_minutes <= 0 or args.trip_minutes <= 0:
            raise ValueError("--shift-minutes and --trip-minutes must be positive")
        engine = create_database_engine(Settings())
        with Session(engine) as session:
            fleets = demo_fleet.plan_fleet(
                session, args.date, args.capacities, args.shift_minutes, args.trip_minutes, args.seed
            )
        logger.info(
            "demo fleet for the collection plan of %s: capacities=%s m3, shift=%d min, "
            "assumed trip=%d min, slack=%.0f%% (an estimate, not a guarantee; invented data)",
            args.date, ",".join(map(str, args.capacities)), args.shift_minutes,
            args.trip_minutes, (demo_fleet.SLACK - 1) * 100,
        )
        for fleet in fleets:
            logger.info(
                "%s: stops=%d, load=%.1f m3, trucks created=%d",
                fleet.carrier, fleet.stops, fleet.load_m3, fleet.trucks,
            )
        return 0
    except demo_fleet.NoCollectionPlan:
        logger.error("Demo fleet failed: the collection plan must be built first for this date; nothing was changed")
        return 1
    except demo_fleet.NoLandfills:
        logger.error("Demo fleet failed: no landfill is stored; nothing was changed")
        return 1
    except Exception as error:
        cause = getattr(error, "orig", error)
        reason = f"{type(cause).__name__}: {cause}" if isinstance(error, SQLAlchemyError) else str(error)
        logger.error("Demo fleet failed, nothing was changed: %s", reason)
        return 1
    finally:
        if engine is not None:
            engine.dispose()
