import argparse
import logging
from pathlib import Path
from time import perf_counter

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import Settings, data_dir
from app.infrastructure.database import SYNC_LOCK_TIMEOUT_MS, create_database_engine
from app.interfaces.container_adequacy_import.importer import import_analyses, parse_analysis
from app.services.adequacy_artifacts import ARTIFACT_PATTERN, output_directory

logger = logging.getLogger(__name__)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")
    parser = argparse.ArgumentParser(description="Import validated monthly or dated adequacy GeoJSON into PostgreSQL.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", type=Path, action="append", help="GeoJSON file; repeat for multiple periods")
    group.add_argument("--all", action="store_true", help="Import monthly and dated files in the configured data directory")
    try:
        args = parser.parse_args()
    except SystemExit as error:
        return 0 if error.code == 0 else 1
    started = perf_counter()
    engine = None
    try:
        paths = args.file if args.file else sorted(
            path for path in output_directory(data_dir()).glob("*.geojson")
            if ARTIFACT_PATTERN.fullmatch(path.name)
        )
        if not paths:
            raise ValueError("No adequacy GeoJSON files found; generate or supply --file first")
        records = [parse_analysis(path) for path in paths]
        if len({record["id"] for record in records}) != len(records):
            raise ValueError("Duplicate analysis IDs in selected files")
        total_bytes = sum(path.stat().st_size for path in paths)
        engine = create_database_engine(Settings())
        with engine.begin() as connection:
            connection.execute(text(f"SET LOCAL lock_timeout = {SYNC_LOCK_TIMEOUT_MS}"))
            count = import_analyses(connection, records)
        logger.info("container_adequacy_analyses <- %d GeoJSON files; %d bytes; %.2f seconds",
                    count, total_bytes, perf_counter() - started)
        return 0
    except (OSError, ValueError, TypeError, KeyError) as error:
        logger.error("Adequacy import failed, nothing was changed: %s", error)
        return 1
    except SQLAlchemyError as error:
        logger.error("Adequacy import failed, nothing was changed (%s)", type(error).__name__)
        return 1
    finally:
        if engine is not None:
            engine.dispose()
