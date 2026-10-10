"""Validate the complete source before replacing any stored boundaries.

Checks are structural; they do not establish full polygon topology or repair it.
"""

import json
from math import fsum, isfinite
from pathlib import Path
from typing import TypedDict

from sqlalchemy import Connection, delete, insert

from app.infrastructure.models import DistrictBoundary

SOURCE_FILE_NAME = "vilnius_seniuniju_ribos.geojson"
SUPPORTED_CRS = {"urn:ogc:def:crs:OGC:1.3:CRS84", "OGC:CRS84", "EPSG:4326"}


class DistrictRecord(TypedDict):
    district_name: str
    source_object_id: int
    geometry: dict


def parse_districts(path: Path) -> list[DistrictRecord]:
    try:
        with path.open(encoding="utf-8") as source:
            data = json.load(source)
    except (OSError, ValueError) as error:
        raise ValueError(f"{path}: cannot read district GeoJSON ({type(error).__name__})") from None
    try:
        return validate_collection(data)
    except ValueError as error:
        raise ValueError(f"{path}: {error}") from None


def validate_collection(data: object) -> list[DistrictRecord]:
    if not isinstance(data, dict) or data.get("type") != "FeatureCollection":
        raise ValueError("expected a nonempty FeatureCollection")
    if "crs" in data:
        crs = data["crs"]
        if not (isinstance(crs, dict) and crs.get("type") == "name"
                and isinstance(crs.get("properties"), dict)
                and crs["properties"].get("name") in SUPPORTED_CRS):
            raise ValueError("unsupported CRS; expected longitude/latitude without reprojection")
    features = data.get("features")
    if not isinstance(features, list) or not features:
        raise ValueError("expected a nonempty features array")
    names: set[str] = set()
    source_ids: set[int] = set()
    records: list[DistrictRecord] = []
    for index, feature in enumerate(features, 1):
        label = f"feature {index}"
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            raise ValueError(f"{label}: expected a Feature")
        props = feature.get("properties")
        if not isinstance(props, dict):
            raise ValueError(f"{label}: expected properties")
        name, source_id = props.get("SENIUNIJA"), props.get("OBJECTID")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"{label}: missing or blank SENIUNIJA")
        if type(source_id) is not int or not -(2 ** 31) <= source_id < 2 ** 31:
            raise ValueError(f"{label}: OBJECTID must be a PostgreSQL integer (not boolean)")
        if name in names or source_id in source_ids:
            raise ValueError(f"{label}: duplicate SENIUNIJA or OBJECTID")
        geometry = feature.get("geometry")
        if not isinstance(geometry, dict) or geometry.get("type") != "Polygon":
            raise ValueError(f"{label}: expected Polygon geometry")
        rings = geometry.get("coordinates")
        if not isinstance(rings, list) or not rings:
            raise ValueError(f"{label}: missing Polygon rings")
        for ring_index, ring in enumerate(rings, 1):
            ring_label = f"{label}, ring {ring_index}"
            if not isinstance(ring, list) or len(ring) < 4:
                raise ValueError(f"{ring_label}: at least four positions required")
            for position in ring:
                if not (isinstance(position, list) and len(position) == 2
                        and all(type(n) in (int, float) and isfinite(n) for n in position)
                        and -180 <= position[0] <= 180 and -90 <= position[1] <= 90):
                    raise ValueError(f"{ring_label}: invalid 2D longitude/latitude position")
            if ring[0] != ring[-1]:
                raise ValueError(f"{ring_label}: unclosed ring")
            if len({tuple(p) for p in ring[:-1]}) < 3:
                raise ValueError(f"{ring_label}: at least three distinct vertices required")
            # Translate to the first vertex to avoid cancellation around large lon/lat values.
            x, y = ring[0]
            area = fsum((a[0] - x) * (b[1] - y) - (b[0] - x) * (a[1] - y)
                        for a, b in zip(ring, ring[1:]))
            if area == 0:
                raise ValueError(f"{ring_label}: zero signed area")
        names.add(name)
        source_ids.add(source_id)
        records.append({"district_name": name, "source_object_id": source_id,
                        "geometry": {"type": "Polygon", "coordinates": rings}})
    return records


def replace_catalog(connection: Connection, records: list[DistrictRecord]) -> int:
    """Replace parsed records within the caller's transaction; never commit here."""
    if not records:
        raise ValueError("refusing an empty district replacement")
    connection.execute(delete(DistrictBoundary))
    connection.execute(insert(DistrictBoundary), records)
    return len(records)
