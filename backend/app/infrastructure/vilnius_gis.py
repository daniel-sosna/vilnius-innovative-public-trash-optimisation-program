import json
import logging
import math
from dataclasses import dataclass
from typing import TypedDict
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)
PAGE_SIZE = 1_000


class BinValues(TypedDict):
    id: int
    lat: float
    lon: float
    address: str | None


@dataclass(frozen=True)
class GISSnapshot:
    bins: list[BinValues]
    retrieved: int
    skipped: int


def map_feature(feature: object) -> BinValues:
    if not isinstance(feature, dict):
        raise ValueError("feature is not an object")
    properties = feature.get("properties")
    if not isinstance(properties, dict):
        raise ValueError("missing feature properties")
    bin_id = properties.get("KAIKS_NR")
    if type(bin_id) is not int or not -(2**31) <= bin_id < 2**31:
        raise ValueError("KAIKS_NR is not a usable PostgreSQL integer")

    geometry = feature.get("geometry")
    if not isinstance(geometry, dict):
        raise ValueError("missing geometry")
    try:
        if geometry.get("type") == "Polygon":
            point = geometry["coordinates"][0][0]
        elif geometry.get("type") == "MultiPolygon":
            point = geometry["coordinates"][0][0][0]
        else:
            raise ValueError("unsupported geometry type")
    except (KeyError, IndexError, TypeError):
        raise ValueError("missing first polygon coordinate") from None
    if not isinstance(point, list) or len(point) < 2:
        raise ValueError("first coordinate is not a longitude/latitude pair")
    lon, lat = point[:2]
    for value, bound, name in ((lon, 180, "longitude"), (lat, 90, "latitude")):
        if (
            type(value) not in (int, float)
            or not -bound <= value <= bound
            or not math.isfinite(value)
        ):
            raise ValueError(f"unusable {name}")

    address = properties.get("ADRESAS")
    if not isinstance(address, str) or not address.strip():
        logger.warning("Bin %s: missing/blank/nontext ADRESAS; using NULL", bin_id)
        address = None
    return {"id": bin_id, "lat": float(lat), "lon": float(lon), "address": address}


def fetch_bins(source_url: str, timeout: float) -> GISSnapshot:
    bins: list[BinValues] = []
    seen: set[int] = set()
    retrieved = skipped = offset = 0
    url_parts = urlsplit(source_url)
    while True:
        query = urlencode(
            {
                "where": "1=1",
                "outFields": "KAIKS_NR,ADRESAS",
                "returnGeometry": "true",
                "outSR": 4326,
                "f": "geojson",
                "resultRecordCount": PAGE_SIZE,
                "resultOffset": offset,
                "orderByFields": "OBJECTID ASC",
            }
        )
        request = Request(
            urlunsplit(url_parts._replace(query=query, fragment="")),
            headers={"User-Agent": "VipTop/0.1", "Accept": "application/json"},
        )
        with urlopen(request, timeout=timeout) as response:
            collection = json.load(response)
        if (
            not isinstance(collection, dict)
            or "error" in collection
            or collection.get("type") != "FeatureCollection"
            or not isinstance(collection.get("features"), list)
        ):
            raise ValueError(f"GIS page at offset {offset} is not a FeatureCollection")

        features = collection["features"]
        retrieved += len(features)
        for position, feature in enumerate(features):
            try:
                values = map_feature(feature)
            except ValueError as error:
                skipped += 1
                properties = (
                    feature.get("properties") if isinstance(feature, dict) else None
                )
                identifier = (
                    properties.get("KAIKS_NR") if isinstance(properties, dict) else None
                )
                logger.warning(
                    "Skipping GIS feature offset=%s position=%s KAIKS_NR=%r: %s",
                    offset,
                    position,
                    identifier,
                    error,
                )
                continue
            if values["id"] in seen:
                raise ValueError(f"duplicate usable KAIKS_NR {values['id']}")
            seen.add(values["id"])
            bins.append(values)

        collection_properties = collection.get("properties")
        flags = [collection.get("exceededTransferLimit", False)]
        if isinstance(collection_properties, dict):
            flags.append(collection_properties.get("exceededTransferLimit", False))
        if any(type(flag) is not bool for flag in flags):
            raise ValueError(f"invalid GIS continuation flag at offset {offset}")
        if not any(flags):
            return GISSnapshot(bins=bins, retrieved=retrieved, skipped=skipped)
        offset += PAGE_SIZE
