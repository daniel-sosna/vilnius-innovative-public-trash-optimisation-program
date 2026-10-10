from math import isfinite

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.models import Bin, Landfill, PopulationCell


def bin_features(session: Session) -> dict:
    rows = session.execute(
        select(
            Bin.id,
            Bin.longitude,
            Bin.latitude,
            Bin.waste_type,
            Bin.inventory_number,
            Bin.capacity_m3,
        ).order_by(Bin.id)
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
                    "inventory_number": row["inventory_number"],
                    "waste_type": row["waste_type"],
                    "capacity_m3": (
                        float(row["capacity_m3"])
                        if row["capacity_m3"] is not None
                        else None
                    ),
                },
            }
            for row in rows
            if row["longitude"] is not None
            and row["latitude"] is not None
            and isfinite(row["longitude"])
            and isfinite(row["latitude"])
            and -180 <= row["longitude"] <= 180
            and -90 <= row["latitude"] <= 90
        ],
    }


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


def population_features(session: Session) -> dict:
    rows = session.execute(
        select(
            PopulationCell.id,
            PopulationCell.geometry,
            PopulationCell.density_per_ha,
            PopulationCell.suppressed,
            PopulationCell.area_ha,
            PopulationCell.residents,
        ).order_by(PopulationCell.id)
    ).mappings()
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": row["id"],
                "geometry": {"type": "Polygon", "coordinates": row["geometry"]},
                "properties": {
                    "density_per_ha": row["density_per_ha"],
                    "suppressed": row["suppressed"],
                    "area_ha": row["area_ha"],
                    # Missing source density has no known resident estimate.
                    # The allocation pipeline's stored zero is only a placeholder.
                    "residents": row["residents"]
                    if row["density_per_ha"] is not None or row["suppressed"]
                    else None,
                },
            }
            for row in rows
        ],
    }
