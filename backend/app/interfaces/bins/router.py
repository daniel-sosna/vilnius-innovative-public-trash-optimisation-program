from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query

from app.interfaces.bins.schemas import (
    BinDeleteResult, HistoryPage, PublicBin, ResidentRequestSuccess,
)
from app.interfaces.collection_session import CollectionSession
from app.interfaces.collection_write_session import CollectionWriteSession
from app.interfaces.resident_request_session import ResidentRequestSession
from app.services import bins, resident_requests

router = APIRouter(prefix="/bins", tags=["Bins"])


@router.delete("/{bin_id}", response_model=BinDeleteResult)
def delete_bin(session: CollectionWriteSession, bin_id: Annotated[int, Path(ge=1)]) -> dict:
    try:
        return bins.delete_bin(session, bin_id)
    except bins.BinNotFoundError:
        raise HTTPException(status_code=404, detail="Bin not found") from None


@router.get("/{bin_id}", response_model=PublicBin)
def get_bin(session: CollectionSession, bin_id: Annotated[int, Path(ge=1)]) -> dict:
    try:
        return bins.get_bin(session, bin_id)
    except bins.BinNotFoundError:
        raise HTTPException(status_code=404, detail="Bin not found") from None


@router.post(
    "/{bin_id}/resident-requests",
    response_model=ResidentRequestSuccess,
    status_code=201,
)
def create_resident_request(
    session: ResidentRequestSession, bin_id: Annotated[int, Path(ge=1)]
) -> dict:
    try:
        return resident_requests.create_request(session, bin_id)
    except bins.BinNotFoundError:
        raise HTTPException(status_code=404, detail="Bin not found") from None


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
