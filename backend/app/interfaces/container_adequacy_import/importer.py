"""Validate all inputs before atomically upserting selected months."""

import hashlib
import json
from pathlib import Path

from sqlalchemy import Connection
from sqlalchemy.dialects.postgresql import insert

from app.infrastructure.models import ContainerAdequacyAnalysis
from app.services.adequacy_artifacts import validate_artifact


def reject_constant(value: str) -> None:
    raise ValueError(f"Invalid JSON constant: {value}")


def parse_analysis(path: Path) -> dict:
    content = path.read_bytes()
    document = validate_artifact(json.loads(content, parse_constant=reject_constant))
    return {"id": document["analysis"]["id"], "revision": hashlib.sha256(content).hexdigest(),
            "type": document["type"], "analysis": document["analysis"], "features": document["features"]}


def import_analyses(connection: Connection, records: list[dict]) -> int:
    """Caller owns transaction; unrelated months are never deleted."""
    table = ContainerAdequacyAnalysis.__table__
    for record in records:
        statement = insert(table).values(record)
        connection.execute(statement.on_conflict_do_update(
            index_elements=[table.c.id],
            set_={key: statement.excluded[key] for key in ("revision", "type", "analysis", "features")},
            where=table.c.revision != statement.excluded.revision,
        ))
    return len(records)
