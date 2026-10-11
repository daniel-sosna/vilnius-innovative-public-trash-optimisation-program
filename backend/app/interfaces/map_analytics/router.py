import asyncio
import json
import logging
from contextlib import suppress

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import StreamingResponse

from app.core.config import Settings
from app.integrations.openai import ResponsesProvider, ProviderFailure
from app.services.adequacy_catalog import get_analysis, list_analyses
from app.services.analytics_agent.contracts import AnalyzeRequest, AnalysisResponse, RunContext
from app.services.analytics_agent.run import analyze

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


@router.post("/agent/analyze", response_model=AnalysisResponse)
async def analyze_area(body: AnalyzeRequest, request: Request):
    settings = Settings()
    key = settings.openai_api_key.get_secret_value().strip() if settings.openai_api_key else ''
    model = (settings.openai_model or '').strip()
    if not key or not model:
        raise HTTPException(status_code=503, detail={'code': 'analysis_configuration', 'message': 'Analysis requires backend OpenAI key and model configuration.'})
    context = RunContext(body.bbox)
    if 'text/event-stream' in request.headers.get('accept', ''):
        async def events():
            queue = asyncio.Queue()
            loop = asyncio.get_running_loop()
            def progress(event):
                try:
                    running_loop = asyncio.get_running_loop()
                except RuntimeError:
                    running_loop = None
                if running_loop is loop:
                    queue.put_nowait(('progress', event))
                else:
                    loop.call_soon_threadsafe(queue.put_nowait, ('progress', event))
            async def execute():
                try:
                    result = await analyze(request.app.state.analytics_sessions, body.bbox, ResponsesProvider(key, model), context, progress)
                    await queue.put(('result', result.model_dump(mode='json')))
                except Exception:
                    await queue.put(('error', {'message': 'Analizės atlikti nepavyko. Bandykite dar kartą.'}))
            task = asyncio.create_task(execute())
            try:
                while True:
                    event, data = await queue.get()
                    yield f'event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n'
                    if event in ('result', 'error'):
                        break
            finally:
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task
        return StreamingResponse(events(), media_type='text/event-stream', headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})
    try:
        return await analyze(request.app.state.analytics_sessions, body.bbox, ResponsesProvider(key, model), context)
    except ProviderFailure:
        raise HTTPException(status_code=502, detail={'code': 'provider_failed', 'message': 'Analysis provider request failed. Retry explicitly.'}) from None
