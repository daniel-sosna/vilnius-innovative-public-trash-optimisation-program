from fastapi import APIRouter

from app.interfaces.collection_session import CollectionSession
from app.interfaces.map_analytics.schemas import (
    LandfillFeatureCollection,
    PopulationFeatureCollection,
)
from app.services.map_analytics import landfill_features, population_features

router = APIRouter(prefix="/map-analytics", tags=["Map analytics"])


@router.get("/landfills", response_model=LandfillFeatureCollection)
def landfills(session: CollectionSession) -> dict:
    return landfill_features(session)


@router.get("/population-cells", response_model=PopulationFeatureCollection)
def population_cells(session: CollectionSession) -> dict:
    return population_features(session)
