import logging
from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response
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
router = APIRouter(prefix="/trucks", tags=["Trucks"])


def database_session(request: Request) -> Iterator[Session]:
    with request.app.state.sessions() as session:
        try:
            yield session
        except trucks.TruckNotFound:
            session.rollback()
            raise HTTPException(status_code=404, detail="Truck not found") from None
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
    min_max_bins_per_trip: Annotated[int | None, Query(ge=1, le=99)] = None,
    max_max_bins_per_trip: Annotated[int | None, Query(ge=1, le=99)] = None,
) -> dict:
    if (
        min_max_bins_per_trip is not None
        and max_max_bins_per_trip is not None
        and min_max_bins_per_trip > max_max_bins_per_trip
    ):
        raise HTTPException(
            status_code=422,
            detail=[
                {
                    "loc": ["query", "min_max_bins_per_trip"],
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
        minimum=min_max_bins_per_trip,
        maximum=max_max_bins_per_trip,
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
