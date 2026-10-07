import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from app.core.config import Settings
from app.infrastructure.database import create_database_engine, create_session_factory
from app.services.bin_sync import synchronize_bins
from fastapi import FastAPI

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s"
    )
    settings = Settings()
    engine = create_database_engine(settings)
    sessions = create_session_factory(engine)
    stop = asyncio.Event()

    async def attempt() -> None:
        try:
            await asyncio.to_thread(synchronize_bins, settings, sessions)
        except Exception as error:
            logger.error("Bin synchronization failed; retaining stored data: %s", error)

    async def periodically() -> None:
        while not stop.is_set():
            try:
                await asyncio.wait_for(
                    stop.wait(), timeout=settings.bin_sync_interval_seconds
                )
            except TimeoutError:
                if not stop.is_set():
                    await attempt()

    try:
        await attempt()
        task = asyncio.create_task(periodically(), name="bin-synchronization")
        logger.info(
            "Next bin synchronization in %s seconds", settings.bin_sync_interval_seconds
        )
        try:
            yield
        finally:
            stop.set()
            # Cancelling to_thread would leave the underlying import running.
            await task
    finally:
        engine.dispose()


app = FastAPI(lifespan=lifespan)
