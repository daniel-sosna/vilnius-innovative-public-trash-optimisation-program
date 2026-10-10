from fastapi import APIRouter

from app.interfaces.collection_session import CollectionSession
from app.interfaces.map_analytics.schemas import LandfillFeatureCollection
from app.services.map_analytics import landfill_features

router = APIRouter(prefix="/map-analytics", tags=["Map analytics"])


@router.get("/landfills", response_model=LandfillFeatureCollection)
def landfills(session: CollectionSession) -> dict:
    return landfill_features(session)
