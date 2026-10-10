import logging
from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.interfaces.landfills.schemas import LandfillResponse
from app.services import landfills

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/landfills", tags=["Landfills"])


def database_session(request: Request) -> Iterator[Session]:
    try:
        with request.app.state.sessions() as session:
            yield session
    except SQLAlchemyError as error:
        logger.error("Landfill read failed (%s)", type(error).__name__)
        raise HTTPException(status_code=500, detail="Landfill read failed") from None


@router.get("", response_model=list[LandfillResponse])
def list_landfills(
    session: Annotated[Session, Depends(database_session)],
) -> list[dict]:
    return landfills.list_landfills(session)
