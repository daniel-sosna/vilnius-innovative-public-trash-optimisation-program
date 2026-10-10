from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, Response

from app.interfaces.collection_session import CollectionSession
from app.interfaces.collection_write_session import CollectionWriteSession
from app.interfaces.sites.schemas import (
    BinCreate, BinPage, BinSummary, SiteCreate, SiteDetail, SitePage, SiteStats, SiteSummary,
)
from app.services import sites

router = APIRouter(prefix="/sites", tags=["Sites"])


@router.post("", response_model=SiteSummary, status_code=201)
def create_site(payload: SiteCreate, session: CollectionWriteSession) -> dict:
    return sites.create_site(session, payload.model_dump())


@router.get("", response_model=SitePage)
def list_sites(
    session: CollectionSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 15,
    address: str | None = None,
) -> dict:
    return sites.list_sites(session, page=page, page_size=page_size, address=address)


# Keep this static route before any future /{site_id} route.
@router.get("/stats", response_model=SiteStats)
def get_stats(session: CollectionSession) -> dict:
    return sites.get_stats(session)


@router.post("/{site_id}/bins", response_model=BinSummary, status_code=201)
def add_bin(
    payload: BinCreate, session: CollectionWriteSession,
    site_id: Annotated[int, Path(ge=1)],
) -> dict:
    try:
        return sites.add_bin(session, site_id, payload.model_dump())
    except sites.SiteNotFoundError:
        raise HTTPException(status_code=404, detail="Site not found") from None


@router.delete("/{site_id}", status_code=204)
def delete_site(
    session: CollectionWriteSession, site_id: Annotated[int, Path(ge=1)]
) -> Response:
    try:
        sites.delete_site(session, site_id)
    except sites.SiteNotFoundError:
        raise HTTPException(status_code=404, detail="Site not found") from None
    return Response(status_code=204)


@router.get("/{site_id}", response_model=SiteDetail)
def get_site(session: CollectionSession, site_id: Annotated[int, Path(ge=1)]) -> dict:
    try:
        return sites.get_site(session, site_id)
    except sites.SiteNotFoundError:
        raise HTTPException(status_code=404, detail="Site not found") from None


@router.get("/{site_id}/bins", response_model=BinPage)
def list_bins(
    session: CollectionSession,
    site_id: Annotated[int, Path(ge=1)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 10,
) -> dict:
    try:
        return sites.list_bins(session, site_id, page=page, page_size=page_size)
    except sites.SiteNotFoundError:
        raise HTTPException(status_code=404, detail="Site not found") from None
