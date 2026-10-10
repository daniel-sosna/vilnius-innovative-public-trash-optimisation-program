import argparse
import logging
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import Settings, data_dir
from app.infrastructure.database import SYNC_LOCK_TIMEOUT_MS, create_database_engine
from app.interfaces.district_boundaries.catalog import SOURCE_FILE_NAME, parse_districts, replace_catalog

logger = logging.getLogger(__name__)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")
    engine = None
    try:
        parser = argparse.ArgumentParser(description="Replace the stored district catalog from GeoJSON.")
        parser.add_argument("--file", type=Path, default=data_dir() / SOURCE_FILE_NAME,
                            help="GeoJSON source (default: configured data directory)")
        try:
            args = parser.parse_args()
        except SystemExit as error:
            return 0 if error.code == 0 else 1
        records = parse_districts(args.file)
        engine = create_database_engine(Settings())
        with engine.begin() as connection:
            connection.execute(text(f"SET LOCAL lock_timeout = {SYNC_LOCK_TIMEOUT_MS}"))
            count = replace_catalog(connection, records)
        logger.info("district_boundaries <- %s: %d districts", args.file, count)
        return 0
    except Exception as error:
        # DB/configuration exceptions can contain credentials, SQL or parameters.
        reason = type(error).__name__ if isinstance(error, SQLAlchemyError) else str(error)
        logger.error("District import failed, catalog unchanged: %s", reason)
        return 1
    finally:
        if engine is not None:
            engine.dispose()
