import argparse
import logging
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import Settings, data_dir
from app.infrastructure.database import SYNC_LOCK_TIMEOUT_MS, create_database_engine
from app.interfaces.service_zones.importer import ZONE_FILE_NAME, parse_zones, replace_zones

logger = logging.getLogger(__name__)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")
    engine = None
    try:
        parser = argparse.ArgumentParser(description="Replace service zones from a validated GeoJSON source.")
        parser.add_argument(
            "--file", type=Path, default=data_dir() / ZONE_FILE_NAME,
            help=f"Source (default: {ZONE_FILE_NAME} in the configured data directory)",
        )
        try:
            args = parser.parse_args()
        except SystemExit as error:
            return 0 if error.code == 0 else 1
        zones = parse_zones(args.file)
        engine = create_database_engine(Settings())
        with engine.begin() as connection:
            connection.execute(text(f"SET LOCAL lock_timeout = {SYNC_LOCK_TIMEOUT_MS}"))
            count = replace_zones(connection, zones)
        logger.info("service_zones <- %s: %d rows", args.file, count)
        return 0
    except (OSError, ValueError) as error:
        logger.error("Service-zone import failed, nothing was changed: %s", error)
        return 1
    except SQLAlchemyError as error:
        logger.error("Service-zone import failed, nothing was changed (%s)", type(error).__name__)
        return 1
    finally:
        if engine is not None:
            engine.dispose()
