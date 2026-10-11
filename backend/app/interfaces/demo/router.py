import logging

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy.exc import SQLAlchemyError

from app.interfaces.demo.schemas import PredictionRequest, PredictionResponse, NavigationRequest, NavigationResponse
from app.services.demo_navigation import navigate
from app.services.demo_prediction import DemoError, predict
from app.services.demo_prerequisites import DemoPrerequisiteError
from app.services.demo_driving import driving_route
from app.interfaces.demo.schemas import DrivingRouteResponse

router = APIRouter(prefix="/demo", tags=["Demo"])
logger = logging.getLogger(__name__)


def execute(operation):
    try:
        return operation()
    except DemoError as error:
        raise HTTPException(error.status, detail={"code": error.code, "message": str(error)}) from None
    except (DemoPrerequisiteError, ImportError, FileNotFoundError):
        raise HTTPException(503, detail={"code": "inference_prerequisites", "message": "Trūksta prognozavimo failų arba bibliotekų. Patikrinkite DEMO_*_PATH ir įdiekite užrakintas priklausomybes."}) from None
    except SQLAlchemyError:
        logger.error("Demo database read failed")
        raise HTTPException(503, detail={"code": "database_unavailable", "message": "Duomenų bazė nepasiekiama. Patikrinkite, ar paleistas ir užpildytas serveris."}) from None
    except ValueError:
        logger.exception("Invalid demo inference data")
        raise HTTPException(422, detail={"code": "inference_data", "message": "Prognozavimo duomenys arba modelis netinkami. Patikrinkite pateiktus CSV ir modelio suderinamumą."}) from None
    except Exception:
        logger.exception("Demo operation failed")
        raise HTTPException(500, detail={"code": "demo_failed", "message": "Demonstracijos veiksmas nepavyko. Patikrinkite serverio žurnalą ir bandykite dar kartą."}) from None


@router.post("/predictions", response_model=PredictionResponse)
def predictions(body: PredictionRequest, request: Request):
    return execute(lambda: predict(body.project_date, request.app.state.sessions))


@router.post("/navigation", response_model=NavigationResponse)
def navigation(body: NavigationRequest, request: Request):
    return execute(lambda: navigate(body.forecast_date, body.bin_ids, request.app.state.sessions))


@router.get("/driving-route", response_model=DrivingRouteResponse)
def driving():
    return execute(driving_route)
