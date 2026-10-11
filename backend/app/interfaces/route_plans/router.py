from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.interfaces.collection_session import CollectionSession
from app.interfaces.route_plans.schemas import AvailablePlan, RoutePlanResponse
from app.services import route_plan

router = APIRouter(prefix="/route-plans", tags=["Route plans"])


@router.get("/available", response_model=list[AvailablePlan])
def available_plans(session: CollectionSession) -> list[dict]:
    return route_plan.list_available(session)


@router.get("", response_model=RoutePlanResponse)
def read_plan(
    session: CollectionSession,
    date: Annotated[date, Query()],
    waste_carrier: Annotated[str, Query(min_length=1)],
) -> dict:
    plan = route_plan.get_stored_plan(session, date, waste_carrier)
    if plan is None:
        raise HTTPException(status_code=404, detail="Route plan not found")
    return plan
