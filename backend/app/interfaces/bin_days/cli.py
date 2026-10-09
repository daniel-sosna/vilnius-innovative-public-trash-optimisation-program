import argparse
import logging
from datetime import date

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import Settings
from app.infrastructure.database import SYNC_LOCK_TIMEOUT_MS, create_database_engine

logger = logging.getLogger(__name__)

# Five calendar years with two leap days, e.g. 2027-03-01..2032-02-29.
MAX_DAYS = 1827

# Season: 1 winter (Dec-Feb), 2 spring, 3 summer, 4 autumn (Sep-Nov).
REBUILD_SQL = text(
    """
    INSERT INTO bin_days (
        bin_id, date, day_of_week, week_of_year, month, season,
        site_id, waste_type, capacity_m3, sub_district, object_group
    )
    SELECT b.id, d.day,
           EXTRACT(ISODOW FROM d.day),
           EXTRACT(WEEK FROM d.day),
           EXTRACT(MONTH FROM d.day),
           EXTRACT(MONTH FROM d.day)::int % 12 / 3 + 1,
           b.site_id, b.waste_type, b.capacity_m3, b.sub_district, b.object_group
    FROM (
        SELECT ts::date AS day
        FROM generate_series(CAST(:start AS date), CAST(:end AS date), interval '1 day') AS ts
    ) AS d
    CROSS JOIN bins AS b
    WHERE b.sub_district IS NOT NULL
    """
)


def iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a YYYY-MM-DD date: {value!r}") from None


def rebuild(engine, start: date, end: date) -> tuple[int, int, int]:
    """Replace bin_days with the grid for start..end; return (rows, included, excluded)."""
    with engine.begin() as connection:
        connection.execute(text(f"SET LOCAL lock_timeout = {SYNC_LOCK_TIMEOUT_MS}"))
        connection.execute(text("TRUNCATE bin_days"))
        rows = connection.execute(REBUILD_SQL, {"start": start, "end": end}).rowcount
        included = connection.execute(
            text("SELECT count(DISTINCT bin_id) FROM bin_days")
        ).scalar_one()
        excluded = connection.execute(
            text("SELECT count(*) FROM bins WHERE sub_district IS NULL")
        ).scalar_one()
    return rows, included, excluded


def main() -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s"
    )
    engine = None
    try:
        parser = argparse.ArgumentParser(
            description="Replace bin_days with one row per bin (with a sub-district) "
            "per day from --start to --end inclusive."
        )
        parser.add_argument("--start", type=iso_date, required=True, help="First day, YYYY-MM-DD")
        parser.add_argument("--end", type=iso_date, required=True, help="Last day, YYYY-MM-DD")
        try:
            args = parser.parse_args()
        except SystemExit as error:
            return 0 if error.code == 0 else 1
        if args.start > args.end:
            logger.error(
                "Bin-day rebuild failed: range is reversed (start %s is after end %s)",
                args.start,
                args.end,
            )
            return 1
        days = (args.end - args.start).days + 1
        if days > MAX_DAYS:
            logger.error(
                "Bin-day rebuild failed: %d days requested, at most %d (five years) allowed",
                days,
                MAX_DAYS,
            )
            return 1
        engine = create_database_engine(Settings())
        rows, included, excluded = rebuild(engine, args.start, args.end)
        logger.info(
            "bin_days rebuilt for %s..%s (%d days): %d bins included, "
            "%d excluded without sub_district, %d rows",
            args.start,
            args.end,
            days,
            included,
            excluded,
            rows,
        )
        return 0
    except Exception as error:
        cause = getattr(error, "orig", error)
        reason = (
            f"{type(cause).__name__}: {cause}"
            if isinstance(error, SQLAlchemyError)
            else str(error)
        )
        logger.error("Bin-day rebuild failed, nothing was changed: %s", reason)
        return 1
    finally:
        if engine is not None:
            engine.dispose()
