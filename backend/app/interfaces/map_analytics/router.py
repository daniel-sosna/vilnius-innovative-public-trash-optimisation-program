from fastapi import APIRouter, HTTPException, Response
import json
import logging

from app.services.adequacy_catalog import get_analysis, list_analyses

from app.interfaces.collection_session import CollectionSession
from app.interfaces.map_analytics.schemas import (
    BinFeatureCollection,
    DistrictFeatureCollection,
    LandfillFeatureCollection,
    PopulationFeatureCollection,
    ServiceZoneFeatureCollection,
    AdequacyCatalog,
)
from app.services.map_analytics import (
    bin_features, district_features, landfill_features, population_features, service_zone_features,
)

router = APIRouter(prefix="/map-analytics", tags=["Map analytics"])
logger = logging.getLogger(__name__)


@router.get("/adequacy-analyses", response_model=AdequacyCatalog)
def adequacy_catalog(session: CollectionSession) -> dict:
    try:
        return list_analyses(session)
    except (OSError, ValueError, TypeError, KeyError):
        logger.exception("Cannot read saved adequacy catalog")
        raise HTTPException(500, "Cannot read saved adequacy analyses") from None


@router.get("/adequacy-analyses/{analysis_id}")
def adequacy_analysis(analysis_id: str, session: CollectionSession) -> Response:
    try:
        document, revision = get_analysis(session, analysis_id)
        return Response(json.dumps(document, ensure_ascii=False, separators=(",", ":"), allow_nan=False),
                        media_type="application/geo+json", headers={"ETag": f'"{revision}"'})
    except FileNotFoundError:
        raise HTTPException(404, "Unknown adequacy analysis") from None
    except (OSError, ValueError, TypeError, KeyError):
        logger.exception("Cannot read saved adequacy analysis")
        raise HTTPException(500, "Cannot read saved adequacy analysis") from None


@router.get("/district-boundaries", response_model=DistrictFeatureCollection)
def district_boundaries(session: CollectionSession) -> dict:
    return district_features(session)


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
