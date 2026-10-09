from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import Settings
from app.infrastructure.database import create_database_engine, create_session_factory
from app.interfaces.bins.router import router as bins_router
from app.interfaces.sites.router import router as sites_router
from app.interfaces.trucks.router import router as trucks_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = create_database_engine(Settings())
    app.state.sessions = create_session_factory(engine)
    try:
        yield
    finally:
        engine.dispose()


app = FastAPI(title="VipTop", lifespan=lifespan)
app.include_router(trucks_router)
app.include_router(sites_router)
app.include_router(bins_router)
