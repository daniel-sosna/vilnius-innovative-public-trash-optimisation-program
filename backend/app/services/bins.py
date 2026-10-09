from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.infrastructure.models import Bin, BinHist


class BinNotFoundError(Exception):
    pass


def get_history(session: Session, bin_id: int, *, page: int, page_size: int) -> dict:
    if (
        bin_id > 2**63 - 1
        or session.scalar(select(Bin.id).where(Bin.id == bin_id)) is None
    ):
        raise BinNotFoundError

    total, successful, unsuccessful = session.execute(
        select(
            func.count(BinHist.id),
            func.count(BinHist.id).filter(BinHist.was_serviced.is_(True)),
            func.count(BinHist.id).filter(BinHist.was_serviced.is_(False)),
        ).where(BinHist.bin_id == bin_id)
    ).one()
    # The aggregate is independent of LIMIT/OFFSET and shares the page snapshot.
    success = (
        round(100 * successful / (successful + unsuccessful), 1) if total else None
    )
    failure = round(100 - success, 1) if success is not None else None
    offset = (page - 1) * page_size
    rows = (
        []
        if offset >= total
        else session.execute(
            select(
                BinHist.id,
                BinHist.date,
                BinHist.was_serviced,
                BinHist.non_serviced_reason,
                BinHist.fill_level,
            )
            .where(BinHist.bin_id == bin_id)
            .order_by(BinHist.date.desc(), BinHist.id.desc())
            .offset(offset)
            .limit(page_size)
        )
        .mappings()
        .all()
    )
    return {
        "items": [dict(row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "successful_service_percentage": success,
        "unsuccessful_service_percentage": failure,
    }
