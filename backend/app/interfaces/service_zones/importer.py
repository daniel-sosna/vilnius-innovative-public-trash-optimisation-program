"""Validate a complete source before replacing zones on the caller's transaction."""

import json
import math
from pathlib import Path

from sqlalchemy import Connection, insert, text

from app.infrastructure.models import ServiceZone

ZONE_FILE_NAME = "service_zones.geojson"
CRS84_NAMES = {"urn:ogc:def:crs:OGC:1.3:CRS84", "OGC:CRS84"}


def reject_constant(value: str) -> None:
    raise ValueError(f"Invalid JSON constant: {value}")


def parse_zones(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as source:
        data = json.load(source, parse_constant=reject_constant)
    if not isinstance(data, dict) or data.get("type") != "FeatureCollection":
        raise ValueError("Expected a GeoJSON FeatureCollection")
    features = data.get("features")
    if not isinstance(features, list):
        raise ValueError("FeatureCollection.features must be an array")
    crs = data.get("crs")
    if crs is not None and (
        not isinstance(crs, dict)
        or crs.get("type") != "name"
        or not isinstance(crs.get("properties"), dict)
        or not isinstance(crs["properties"].get("name"), str)
        or crs["properties"].get("name") not in CRS84_NAMES
    ):
        raise ValueError("Unsupported coordinate reference: expected longitude/latitude CRS84")

    zones: list[dict] = []
    numbers: set[int] = set()
    for index, feature in enumerate(features, start=1):
        prefix = f"Feature {index}"
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            raise ValueError(f"{prefix}: expected a GeoJSON Feature")
        properties = feature.get("properties")
        if not isinstance(properties, dict):
            raise ValueError(f"{prefix}: properties must be an object")
        name, number = properties.get("ZONA"), properties.get("ZONOS_NR")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"{prefix}: ZONA must be a nonblank string")
        if type(number) is not int or not -(2**31) <= number < 2**31:
            raise ValueError(f"{prefix}: ZONOS_NR must be a PostgreSQL integer")
        if number in numbers:
            raise ValueError(f"{prefix}: duplicate ZONOS_NR {number}")
        numbers.add(number)
        geometry = feature.get("geometry")
        if not isinstance(geometry, dict) or geometry.get("type") != "Polygon":
            raise ValueError(f"{prefix}: geometry must be a Polygon")
        rings = geometry.get("coordinates")
        if not isinstance(rings, list) or not rings:
            raise ValueError(f"{prefix}: Polygon must contain an exterior ring")
        for ring in rings:
            if not isinstance(ring, list) or len(ring) < 4:
                raise ValueError(f"{prefix}: each ring needs at least four positions")
            for position in ring:
                if (
                    not isinstance(position, list)
                    or len(position) != 2
                    or any(type(value) not in (int, float) for value in position)
                    or not -180 <= position[0] <= 180
                    or not -90 <= position[1] <= 90
                    or not all(math.isfinite(value) for value in position)
                ):
                    raise ValueError(f"{prefix}: expected finite [longitude, latitude] positions")
            if ring[0] != ring[-1]:
                raise ValueError(f"{prefix}: Polygon rings must be closed")
        zones.append({
            "zone_name": name,
            "zone_number": number,
            "geometry": {"type": "Polygon", "coordinates": rings},
        })
    return sorted(zones, key=lambda zone: zone["zone_number"])


def replace_zones(connection: Connection, zones: list[dict]) -> int:
    """Replace only zones; the caller owns commit, rollback and timeouts."""
    connection.execute(text("TRUNCATE service_zones RESTART IDENTITY"))
    if zones:
        connection.execute(insert(ServiceZone.__table__), zones)
    return len(zones)
