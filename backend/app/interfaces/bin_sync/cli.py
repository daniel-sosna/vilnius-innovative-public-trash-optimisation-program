import argparse
import logging

from app.core.config import Settings
from app.infrastructure.database import create_database_engine, create_session_factory
from app.integrations.vasa import DEFAULT_BBOX
from app.services.bin_sync import ImportOptions, synchronize_bins

logger = logging.getLogger(__name__)


def main() -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s"
    )
    engine = None
    try:
        parser = argparse.ArgumentParser(
            description="Manually import VASA bins/history; resume incomplete passes or refresh completed ones."
        )
        parser.add_argument(
            "--max-sites",
            type=int,
            default=10,
            help="Selected site limit; 0 means unlimited (default: 10)",
        )
        parser.add_argument(
            "--max-tiles",
            type=int,
            default=0,
            help="Coverage tile limit; 0 means unlimited",
        )
        parser.add_argument(
            "--workers",
            type=int,
            default=4,
            help="Maximum concurrent source requests (default: 4)",
        )
        parser.add_argument(
            "--zoom", type=int, default=17, help="Tile zoom (default: 17)"
        )
        parser.add_argument(
            "--bbox",
            nargs=4,
            type=float,
            default=DEFAULT_BBOX,
            metavar=("WEST", "SOUTH", "EAST", "NORTH"),
        )
        try:
            args = parser.parse_args()
        except SystemExit as error:
            return 0 if error.code == 0 else 1
        options = ImportOptions(
            tuple(args.bbox), args.zoom, args.workers, args.max_sites, args.max_tiles
        )
        options.validate()
        settings = Settings()
        engine = create_database_engine(settings)
        summary = synchronize_bins(settings, create_session_factory(engine), options)
        return summary.exit_code
    except Exception as error:
        from sqlalchemy.exc import SQLAlchemyError

        reason = (
            type(getattr(error, "orig", error)).__name__
            if isinstance(error, SQLAlchemyError)
            else str(error)
        )
        logger.error("Bin synchronization failed: %s", reason)
        return 1
    finally:
        if engine is not None:
            engine.dispose()
    return 0
