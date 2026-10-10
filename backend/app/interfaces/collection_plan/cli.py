import argparse
import logging
from datetime import date

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.infrastructure.database import create_database_engine
from app.services.collection_plan import build_plan

logger = logging.getLogger(__name__)

DEFAULT_THRESHOLD = 2


def iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a YYYY-MM-DD date: {value!r}") from None


def threshold_level(value: str) -> int:
    try:
        level = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"--threshold is not an integer: {value!r}") from None
    if not 0 <= level <= 4:
        raise argparse.ArgumentTypeError(f"--threshold must be between 0 and 4: {value!r}")
    return level


def main() -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s"
    )
    engine = None
    try:
        parser = argparse.ArgumentParser(
            description="Replace the collection plan of one date: bins whose predicted "
            "fill level is above the threshold, grouped into stops per waste carrier "
            "and site. The prediction is a MOCK (synthetic, seeded from the date)."
        )
        parser.add_argument(
            "--date", type=iso_date, default=None,
            help="Plan date, YYYY-MM-DD (default today)",
        )
        parser.add_argument(
            "--threshold", type=threshold_level, default=DEFAULT_THRESHOLD,
            help="Bins with a predicted fill level strictly above this, 0..4 "
            f"(default {DEFAULT_THRESHOLD})",
        )
        try:
            args = parser.parse_args()
        except SystemExit as error:
            return 0 if error.code == 0 else 1
        day = args.date or date.today()
        engine = create_database_engine(Settings())
        with Session(engine) as session:
            if session.execute(text("SELECT NOT EXISTS (SELECT 1 FROM bins)")).scalar_one():
                logger.error("Collection plan failed: no bins are stored; nothing was changed")
                return 1
            summary = build_plan(session, day, args.threshold)
        logger.info(
            "collection plan rebuilt for %s: threshold=%d (due when fill > threshold), "
            "prediction=MOCK (synthetic, uniform 0..4, seeded from the date)",
            day,
            args.threshold,
        )
        logger.info(
            "bins evaluated=%d, due=%d, bins of the stops without capacity=%d",
            summary.evaluated,
            summary.due,
            summary.without_capacity,
        )
        carriers = {k: v for k, v in summary.stops_per_carrier.items() if k is not None}
        logger.info(
            "stops per carrier: %s; unassigned stops: %d",
            ", ".join(f"{name}={count}" for name, count in sorted(carriers.items())) or "none",
            summary.unassigned_stops,
        )
        return 0
    except Exception as error:
        cause = getattr(error, "orig", error)
        reason = (
            f"{type(cause).__name__}: {cause}"
            if isinstance(error, SQLAlchemyError)
            else str(error)
        )
        logger.error("Collection plan failed, nothing was changed: %s", reason)
        return 1
    finally:
        if engine is not None:
            engine.dispose()
