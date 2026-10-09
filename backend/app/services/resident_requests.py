from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.models import Bin, ResidentRequest
from app.services.bins import BinNotFoundError


def create_request(session: Session, bin_id: int) -> dict:
    if bin_id > 2**63 - 1:
        raise BinNotFoundError
    parent = session.scalar(
        select(Bin.id).where(Bin.id == bin_id).with_for_update(read=True, key_share=True)
    )
    if parent is None:
        raise BinNotFoundError
    session.add(ResidentRequest(bin_id=parent))
    session.flush()
    session.commit()
    return {"success": True}
