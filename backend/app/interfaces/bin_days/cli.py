import argparse
import logging
from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import Settings
from app.infrastructure.database import SYNC_LOCK_TIMEOUT_MS, create_database_engine
from app.interfaces.bin_days.simulation import (
    WARMUP_DAYS,
    Parameters,
    holiday_ordinals,
    simulate_bin,
)

logger = logging.getLogger(__name__)

# Five calendar years with two leap days, e.g. 2027-03-01..2032-02-29.
MAX_DAYS = 1827

# Defaults of the simulation options. The failure probabilities are assumptions.
DEFAULT_SEED = 42
DEFAULT_P_FIRST = 0.028
DEFAULT_P_RETRY1 = 0.40
DEFAULT_P_RETRY2 = 0.70
DEFAULT_HOLIDAY_FACTOR = 2

# Season: 1 winter (Dec-Feb), 2 spring, 3 summer, 4 autumn (Sep-Nov).
INSERT_SQL = text(
    """
    INSERT INTO bin_days (
        bin_id, date, day_of_week, week_of_year, month, season,
        site_id, waste_type, capacity_m3, sub_district, object_group,
        population_cell_id, resident_factor,
        collection_status, holidays_since_last_collection,
        collections_last_28d, missed_collections_28d
    )
    SELECT b.id, s.date,
           EXTRACT(ISODOW FROM s.date),
           EXTRACT(WEEK FROM s.date),
           EXTRACT(MONTH FROM s.date),
           EXTRACT(MONTH FROM s.date)::int % 12 / 3 + 1,
           b.site_id, b.waste_type, b.capacity_m3, b.sub_district, b.object_group,
           p.population_cell_id, p.resident_factor,
           s.collection_status, s.holidays_since_last_collection,
           s.collections_last_28d, s.missed_collections_28d
    FROM simulated_bin_days AS s
    JOIN bins AS b ON b.id = s.bin_id
    JOIN bin_population AS p ON p.bin_id = b.id
    """
)

CREATE_TEMP_SQL = text(
    """
    CREATE TEMP TABLE simulated_bin_days (
        bin_id BIGINT NOT NULL,
        date DATE NOT NULL,
        collection_status TEXT NOT NULL,
        holidays_since_last_collection SMALLINT NOT NULL,
        collections_last_28d SMALLINT NOT NULL,
        missed_collections_28d SMALLINT NOT NULL
    ) ON COMMIT DROP
    """
)

SCHEDULE_SQL = text(
    """
    SELECT s.bin_id, s.date
    FROM bin_schedule AS s
    JOIN bins AS b ON b.id = s.bin_id
    WHERE b.sub_district IS NOT NULL
    ORDER BY s.bin_id
    """
)

MISSING_POPULATION_SQL = text(
    """
    SELECT count(DISTINCT b.id)
    FROM bin_schedule AS s
    JOIN bins AS b ON b.id = s.bin_id
    WHERE b.sub_district IS NOT NULL
      AND NOT EXISTS (SELECT 1 FROM bin_population WHERE bin_id = b.id)
    """
)

EXCLUDED_SQL = text(
    """
    SELECT count(*) FILTER (WHERE sub_district IS NULL),
           count(*) FILTER (
               WHERE sub_district IS NOT NULL
                 AND NOT EXISTS (SELECT 1 FROM bin_schedule WHERE bin_id = bins.id)
           )
    FROM bins
    """
)


@dataclass
class RebuildResult:
    rows: int
    included: int
    no_sub_district: int
    no_schedule: int
    status_counts: Counter


def iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a YYYY-MM-DD date: {value!r}") from None


def probability(name: str):
    def parse(value: str) -> float:
        try:
            number = float(value)
        except ValueError:
            raise argparse.ArgumentTypeError(f"{name} is not a number: {value!r}") from None
        if not 0 <= number <= 1:
            raise argparse.ArgumentTypeError(f"{name} must be between 0 and 1: {value!r}")
        return number

    return parse


def non_negative(value: str) -> float:
    try:
        number = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"--holiday-factor is not a number: {value!r}") from None
    if not number >= 0:
        raise argparse.ArgumentTypeError(f"--holiday-factor must be at least 0: {value!r}")
    return number


def load_schedules(connection) -> dict[int, set[date]]:
    schedules: dict[int, set[date]] = {}
    for bin_id, day in connection.execute(SCHEDULE_SQL):
        schedules.setdefault(bin_id, set()).add(day)
    return schedules


def rebuild(engine, start: date, end: date, params: Parameters) -> RebuildResult:
    """Replace bin_days with the simulated calendar for start..end."""
    holiday_days = holiday_ordinals(start - timedelta(days=WARMUP_DAYS), end)
    status_counts: Counter = Counter()
    with engine.begin() as connection:
        connection.execute(text(f"SET LOCAL lock_timeout = {SYNC_LOCK_TIMEOUT_MS}"))
        missing = connection.execute(MISSING_POPULATION_SQL).scalar_one()
        if missing:
            raise RuntimeError(
                f"{missing} eligible bins have no resident allocation; "
                "run python -m app.interfaces.bin_population first"
            )
        schedules = load_schedules(connection)
        connection.execute(CREATE_TEMP_SQL)
        raw = connection.connection.driver_connection
        with raw.cursor() as cursor:
            with cursor.copy(
                "COPY simulated_bin_days (bin_id, date, collection_status, "
                "holidays_since_last_collection, collections_last_28d, "
                "missed_collections_28d) FROM STDIN"
            ) as copy:
                for bin_id, planned in schedules.items():
                    for day, status, *features in simulate_bin(
                        bin_id, planned, start, end, params, holiday_days
                    ):
                        status_counts[status] += 1
                        copy.write_row((bin_id, day, status, *features))
        connection.execute(text("TRUNCATE bin_days"))
        rows = connection.execute(INSERT_SQL).rowcount
        no_sub_district, no_schedule = connection.execute(EXCLUDED_SQL).one()
    return RebuildResult(rows, len(schedules), no_sub_district, no_schedule, status_counts)


def main() -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s"
    )
    engine = None
    try:
        parser = argparse.ArgumentParser(
            description="Replace bin_days with one row per bin (with a sub-district and "
            "a planned schedule) per day from --start to --end inclusive, with a "
            "simulated collection status."
        )
        parser.add_argument("--start", type=iso_date, required=True, help="First day, YYYY-MM-DD")
        parser.add_argument("--end", type=iso_date, required=True, help="Last day, YYYY-MM-DD")
        parser.add_argument(
            "--seed", type=int, default=DEFAULT_SEED,
            help=f"Random seed (default {DEFAULT_SEED})",
        )
        parser.add_argument(
            "--p-first", type=probability("--p-first"), default=DEFAULT_P_FIRST,
            help=f"Failure probability of a first attempt (default {DEFAULT_P_FIRST})",
        )
        parser.add_argument(
            "--p-retry1", type=probability("--p-retry1"), default=DEFAULT_P_RETRY1,
            help=f"Failure probability of the first retry (default {DEFAULT_P_RETRY1})",
        )
        parser.add_argument(
            "--p-retry2", type=probability("--p-retry2"), default=DEFAULT_P_RETRY2,
            help=f"Failure probability of the second retry (default {DEFAULT_P_RETRY2})",
        )
        parser.add_argument(
            "--holiday-factor", type=non_negative, default=DEFAULT_HOLIDAY_FACTOR,
            help="Failure probability multiplier on public holidays, capped at 0.95 "
            f"(default {DEFAULT_HOLIDAY_FACTOR})",
        )
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
        params = Parameters(
            args.seed, args.p_first, args.p_retry1, args.p_retry2, args.holiday_factor
        )
        engine = create_database_engine(Settings())
        result = rebuild(engine, args.start, args.end, params)
        logger.info(
            "bin_days rebuilt for %s..%s (%d days): %d bins included, "
            "%d excluded without sub_district, %d excluded without schedule, %d rows",
            args.start,
            args.end,
            days,
            result.included,
            result.no_sub_district,
            result.no_schedule,
            result.rows,
        )
        logger.info(
            "simulation: seed=%d p_first=%s p_retry1=%s p_retry2=%s holiday_factor=%s",
            params.seed,
            params.p_first,
            params.p_retry1,
            params.p_retry2,
            params.holiday_factor,
        )
        logger.info(
            "rows per status: %s",
            ", ".join(
                f"{status}={result.status_counts[status]}"
                for status in ("none", "collected", "retry_collected", "failed", "missed")
            ),
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
