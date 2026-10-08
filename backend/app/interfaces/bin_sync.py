import logging

from app.core.config import Settings
from app.infrastructure.database import create_database_engine, create_session_factory
from app.services.bin_sync import synchronize_bins

logger = logging.getLogger(__name__)


def main() -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s"
    )
    engine = None
    try:
        settings = Settings()
        engine = create_database_engine(settings)
        synchronize_bins(settings, create_session_factory(engine))
    except Exception as error:
        logger.error("Bin synchronization failed: %s", error)
        return 1
    finally:
        if engine is not None:
            engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
