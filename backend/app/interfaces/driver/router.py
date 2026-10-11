import logging

from fastapi import APIRouter, HTTPException

from app.interfaces.collection_session import CollectionSession
from app.interfaces.collection_write_session import CollectionWriteSession
from app.interfaces.driver.schemas import (
    RouteRequest,
    RouteResponse,
    ServiceRequest,
    ServiceResponse,
)
from app.services import driver_route, driver_service
from app.services.bins import BinNotFoundError

router = APIRouter(prefix="/driver", tags=["Driver"])
logger = logging.getLogger(__name__)


@router.post("/route", response_model=RouteResponse)
def build_route(body: RouteRequest, session: CollectionSession) -> dict:
    try:
        return driver_route.build_route(session, body.truck_id)
    except driver_route.DriverRouteError as error:
        raise HTTPException(error.status, detail={"code": error.code, "message": str(error)}) from None


@router.post("/service", response_model=ServiceResponse, status_code=201)
def record_service(body: ServiceRequest, session: CollectionWriteSession) -> dict:
    try:
        records = driver_service.record_service(session, [item.model_dump() for item in body.services])
    except BinNotFoundError:
        raise HTTPException(404, detail="Bin not found") from None
    except driver_service.ServiceConflict:
        raise HTTPException(409, detail="Service already recorded") from None
    return {"records": records}
