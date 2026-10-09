import logging
from collections.abc import Iterator
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.interfaces.trucks.schemas import (
    TruckCreate,
    TruckPage,
    TruckPatch,
    TruckResponse,
    TruckStats,
)
from app.services import trucks

logger = logging.getLogger(__name__)


class TruckRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def validated_handler(request: Request) -> Response:
            try:
                return await handler(request)
            except RequestValidationError as error:
                # Nonfinite input cannot itself be encoded in a JSON error body.
                # Return field locations/messages without echoing invalid values.
                detail = [
                    {key: issue[key] for key in ("loc", "msg", "type")}
                    for issue in error.errors()
                ]
                return JSONResponse(status_code=422, content={"detail": detail})

        return validated_handler


router = APIRouter(prefix="/trucks", tags=["Trucks"], route_class=TruckRoute)


def database_session(request: Request) -> Iterator[Session]:
    with request.app.state.sessions() as session:
        try:
            yield session
        except trucks.TruckNotFound:
            session.rollback()
            raise HTTPException(status_code=404, detail="Truck not found") from None
        except trucks.InvalidLandfill:
            session.rollback()
            raise HTTPException(
                status_code=422,
                detail=[
                    {
                        "loc": ["body", "landfill_id"],
                        "msg": "Select an existing landfill",
                        "type": "value_error",
                    }
                ],
            ) from None
        except SQLAlchemyError as error:
            session.rollback()
            logger.error(
                "Truck persistence failed (%s); transaction rolled back",
                type(error).__name__,
            )
            raise HTTPException(
                status_code=500, detail="Truck operation failed"
            ) from None


DatabaseSession = Annotated[Session, Depends(database_session)]
TruckId = Annotated[int, Path(gt=0)]


@router.get("", response_model=TruckPage)
def list_trucks(
    session: DatabaseSession,
    page: Annotated[int, Query(ge=1)] = 1,
    name: str | None = None,
    available: bool | None = None,
    min_max_volume_m3: Annotated[
        Decimal | None, Query(gt=0, allow_inf_nan=False)
    ] = None,
    max_max_volume_m3: Annotated[
        Decimal | None, Query(gt=0, allow_inf_nan=False)
    ] = None,
    waste_carrier: str | None = None,
) -> dict:
    if (
        min_max_volume_m3 is not None
        and max_max_volume_m3 is not None
        and min_max_volume_m3 > max_max_volume_m3
    ):
        raise HTTPException(
            status_code=422,
            detail=[
                {
                    "loc": ["query", "min_max_volume_m3"],
                    "msg": "Minimum cannot exceed maximum",
                    "type": "value_error",
                }
            ],
        )
    return trucks.list_trucks(
        session,
        page=page,
        name=name,
        available=available,
        minimum=min_max_volume_m3,
        maximum=max_max_volume_m3,
        waste_carrier=waste_carrier,
    )


@router.get("/stats", response_model=TruckStats)
def get_stats(session: DatabaseSession) -> dict:
    return trucks.get_stats(session)


@router.get("/{truck_id}", response_model=TruckResponse)
def get_truck(truck_id: TruckId, session: DatabaseSession) -> dict:
    return trucks.get_truck(session, truck_id)


@router.post("", response_model=TruckResponse, status_code=201)
def create_truck(payload: TruckCreate, session: DatabaseSession) -> dict:
    return trucks.create_truck(session, payload.model_dump())


@router.patch("/{truck_id}", response_model=TruckResponse)
def patch_truck(
    truck_id: TruckId, payload: TruckPatch, session: DatabaseSession
) -> dict:
    return trucks.patch_truck(session, truck_id, payload.model_dump(exclude_unset=True))


@router.delete("/{truck_id}", status_code=204)
def delete_truck(truck_id: TruckId, session: DatabaseSession) -> Response:
    trucks.delete_truck(session, truck_id)
    return Response(status_code=204)
