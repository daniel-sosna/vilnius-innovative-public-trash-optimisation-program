from fastapi import APIRouter

from app.interfaces.collection_session import CollectionSession
from app.interfaces.map_analytics.schemas import (
    BinFeatureCollection,
    LandfillFeatureCollection,
    PopulationFeatureCollection,
    ServiceZoneFeatureCollection,
)
from app.services.map_analytics import bin_features, landfill_features, population_features, service_zone_features

router = APIRouter(prefix="/map-analytics", tags=["Map analytics"])


@router.get("/service-zones", response_model=ServiceZoneFeatureCollection)
def service_zones(session: CollectionSession) -> dict:
    return service_zone_features(session)


@router.get("/bins", response_model=BinFeatureCollection)
def bins(session: CollectionSession) -> dict:
    return bin_features(session)


@router.get("/landfills", response_model=LandfillFeatureCollection)
def landfills(session: CollectionSession) -> dict:
    return landfill_features(session)


@router.get("/population-cells", response_model=PopulationFeatureCollection)
def population_cells(session: CollectionSession) -> dict:
    return population_features(session)
