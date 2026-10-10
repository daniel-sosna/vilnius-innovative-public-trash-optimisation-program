from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.models import Landfill


def landfill_features(session: Session) -> dict:
    rows = session.execute(
        select(
            Landfill.id,
            Landfill.longitude,
            Landfill.latitude,
            Landfill.name,
            Landfill.operator,
            Landfill.address,
            Landfill.coordinate_quality,
        ).order_by(Landfill.id)
    ).mappings()
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": row["id"],
                "geometry": {
                    "type": "Point",
                    "coordinates": [row["longitude"], row["latitude"]],
                },
                "properties": {
                    key: row[key]
                    for key in ("name", "operator", "address", "coordinate_quality")
                },
            }
            for row in rows
            if row["longitude"] is not None and row["latitude"] is not None
        ],
    }
