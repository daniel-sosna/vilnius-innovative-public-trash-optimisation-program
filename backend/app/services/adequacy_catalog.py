"""Read imported GeoJSON collections through the existing database snapshot."""

import re
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.models import ContainerAdequacyAnalysis

CATALOG_FIELDS = ("id", "month", "period_start", "period_end", "complete",
                  "schema_version", "method_version", "fill_provenance")


def list_analyses(session: Session, project_date: date | None = None) -> dict:
    rows = session.execute(
        select(ContainerAdequacyAnalysis.analysis, ContainerAdequacyAnalysis.revision)
        .order_by(ContainerAdequacyAnalysis.id.desc())
    ).mappings()
    entries = [{**{key: row["analysis"][key] for key in CATALOG_FIELDS},
                "revision": row["revision"]} for row in rows]
    if project_date is None:
        entries = [entry for entry in entries if entry['schema_version'] == '1' and entry['complete'] is True]
    else:
        cutoff = project_date.isoformat()
        entries = [entry for entry in entries
                   if (entry['schema_version'] == '1' and entry['complete'] is True and entry['period_end'] <= cutoff)
                   or (entry['schema_version'] == '2' and entry['id'] == f'adequacy-{cutoff}')]
    return {"analyses": sorted(entries, key=lambda entry: (entry['period_end'], entry['id']), reverse=True)}


def get_analysis(session: Session, analysis_id: str) -> tuple[dict, str]:
    if not re.fullmatch(r"adequacy-\d{4}-\d{2}(?:-\d{2})?", analysis_id):
        raise FileNotFoundError("Unknown analysis")
    row = session.execute(
        select(ContainerAdequacyAnalysis.__table__)
        .where(ContainerAdequacyAnalysis.id == analysis_id)
    ).mappings().one_or_none()
    if row is None:
        raise FileNotFoundError("Unknown analysis")
    return {"type": row["type"], "analysis": row["analysis"], "features": row["features"]}, row["revision"]
