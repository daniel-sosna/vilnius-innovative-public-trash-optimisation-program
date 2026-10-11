"""Read imported GeoJSON collections through the existing database snapshot."""

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.models import ContainerAdequacyAnalysis

CATALOG_FIELDS = ("id", "month", "period_start", "period_end", "complete",
                  "schema_version", "method_version", "fill_provenance")


def list_analyses(session: Session) -> dict:
    rows = session.execute(
        select(ContainerAdequacyAnalysis.analysis, ContainerAdequacyAnalysis.revision)
        .order_by(ContainerAdequacyAnalysis.id.desc())
    ).mappings()
    return {"analyses": [{**{key: row["analysis"][key] for key in CATALOG_FIELDS},
                          "revision": row["revision"]} for row in rows]}


def get_analysis(session: Session, analysis_id: str) -> tuple[dict, str]:
    if not re.fullmatch(r"adequacy-\d{4}-\d{2}", analysis_id):
        raise FileNotFoundError("Unknown analysis")
    row = session.execute(
        select(ContainerAdequacyAnalysis.__table__)
        .where(ContainerAdequacyAnalysis.id == analysis_id)
    ).mappings().one_or_none()
    if row is None:
        raise FileNotFoundError("Unknown analysis")
    return {"type": row["type"], "analysis": row["analysis"], "features": row["features"]}, row["revision"]
