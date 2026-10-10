import argparse
import logging

from app.core.config import Settings
from app.infrastructure.database import create_database_engine, create_session_factory
from app.services.bin_schedule_sync import NoBinsError, synchronize_schedules
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)
MAX_LISTED_FAILURES = 20


def main() -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s"
    )
    engine = None
    try:
        parser = argparse.ArgumentParser(
            description="Fetch VASA planned collection dates (current month) for stored bins."
        )
        parser.add_argument(
            "--workers",
            type=int,
            default=4,
            help="Maximum concurrent source requests (default: 4)",
        )
        parser.add_argument(
            "--max-bins",
            type=int,
            default=0,
            help="Process only the first N bins by ID; 0 means all (default: 0)",
        )
        try:
            args = parser.parse_args()
        except SystemExit as error:
            return 0 if error.code == 0 else 1
        if args.workers <= 0 or args.max_bins < 0:
            raise ValueError("workers must be positive and max-bins nonnegative")
        settings = Settings()
        engine = create_database_engine(settings)
        summary = synchronize_schedules(
            settings, create_session_factory(engine), args.workers, args.max_bins
        )
        logger.info(
            "Bins processed: %d; with dates: %d; empty: %d; failed: %d; dates stored: %d",
            summary.processed,
            summary.with_dates,
            summary.empty,
            len(summary.failed),
            summary.dates_stored,
        )
        if summary.failed:
            listed = summary.failed[:MAX_LISTED_FAILURES]
            more = len(summary.failed) - len(listed)
            logger.error(
                "Failed external IDs: %s%s",
                ", ".join(map(str, listed)),
                f" (and {more} more)" if more else "",
            )
            return 1
        if args.max_bins:
            logger.info("Run limited to the first %d bins", args.max_bins)
            return 2
        return 0
    except NoBinsError as error:
        logger.error("Schedule synchronization failed: %s", error)
        return 1
    except Exception as error:
        reason = (
            type(getattr(error, "orig", error)).__name__
            if isinstance(error, SQLAlchemyError)
            else str(error)
        )
        logger.error("Schedule synchronization failed: %s", reason)
        return 1
    finally:
        if engine is not None:
            engine.dispose()
