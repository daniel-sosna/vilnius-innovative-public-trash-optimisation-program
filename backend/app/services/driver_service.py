"""Record the driver's fill observations of one stop as serviced bin_hist rows."""

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.infrastructure.models import Bin, BinHist
from app.services.bins import BinNotFoundError


class ServiceConflict(Exception):
    pass


def record_service(session: Session, items: list[dict]) -> list[dict]:
    """Store one serviced row per item in a single transaction.

    Raises BinNotFoundError when any bin is missing (nothing is stored). The timestamp is the
    server's Europe/Vilnius wall clock, as for resident requests.
    """
    ids = [item["bin_id"] for item in items]
    found = set(session.scalars(select(Bin.id).where(Bin.id.in_(ids))))
    if found != set(ids):
        raise BinNotFoundError
    now = func.timezone("Europe/Vilnius", func.statement_timestamp())
    try:
        rows = [
            BinHist(bin_id=item["bin_id"], date=now, was_serviced=True, fill_level=item["fill_level"])
            for item in items
        ]
        session.add_all(rows)
        session.flush()
        records = [
            {"id": row.id, "bin_id": row.bin_id, "date": row.date, "fill_level": row.fill_level}
            for row in rows
        ]
        session.commit()
    except IntegrityError:
        session.rollback()
        raise ServiceConflict from None
    return records
