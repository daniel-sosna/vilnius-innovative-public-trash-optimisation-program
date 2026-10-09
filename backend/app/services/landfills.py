from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.models import Landfill


def list_landfills(session: Session) -> list[dict]:
    rows = session.execute(
        select(*Landfill.__table__.columns).order_by(Landfill.id)
    ).mappings()
    return [dict(row) for row in rows]
