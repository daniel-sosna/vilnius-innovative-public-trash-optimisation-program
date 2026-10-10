from contextlib import asynccontextmanager
from math import isfinite

from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.config import Settings
from app.infrastructure.database import create_database_engine, create_session_factory
from app.interfaces.bins.router import router as bins_router
from app.interfaces.landfills.router import router as landfills_router
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


@app.exception_handler(RequestValidationError)
async def validation_error(_request, error: RequestValidationError):
    # Invalid JSON extensions such as NaN/Infinity must still produce a JSON 422.
    detail = jsonable_encoder(
        error.errors(),
        custom_encoder={float: lambda value: value if isfinite(value) else str(value)},
    )
    return JSONResponse(status_code=422, content={"detail": detail})


app.include_router(trucks_router)
app.include_router(landfills_router)
app.include_router(sites_router)
app.include_router(bins_router)
