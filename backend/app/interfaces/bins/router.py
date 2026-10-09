from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query

from app.interfaces.bins.schemas import HistoryPage
from app.interfaces.collection_session import CollectionSession
from app.services import bins

router = APIRouter(prefix="/bins", tags=["Bins"])


@router.get("/{bin_id}/history", response_model=HistoryPage)
def get_history(
    session: CollectionSession,
    bin_id: Annotated[int, Path(ge=1)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=20)] = 20,
) -> dict:
    try:
        return bins.get_history(session, bin_id, page=page, page_size=page_size)
    except bins.BinNotFoundError:
        raise HTTPException(status_code=404, detail="Bin not found") from None
