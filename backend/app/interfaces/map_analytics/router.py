from fastapi import APIRouter

from app.interfaces.collection_session import CollectionSession
from app.interfaces.map_analytics.schemas import BinFeatureCollection, LandfillFeatureCollection
from app.services.map_analytics import bin_features, landfill_features

router = APIRouter(prefix="/map-analytics", tags=["Map analytics"])


@router.get("/bins", response_model=BinFeatureCollection)
def bins(session: CollectionSession) -> dict:
    return bin_features(session)


@router.get("/landfills", response_model=LandfillFeatureCollection)
def landfills(session: CollectionSession) -> dict:
    return landfill_features(session)
