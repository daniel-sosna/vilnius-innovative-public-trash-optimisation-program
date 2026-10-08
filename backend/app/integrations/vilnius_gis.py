import json
import logging
import math
from dataclasses import dataclass
from typing import TypedDict
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)
PAGE_SIZE = 1_000
TIPAS_MAP = {
    1: "A1 (požeminiai)",
    2: "A3 (požeminiai)",
    3: "B2 (pusiau požeminiai stačiakampiai)",
    4: "B3 (pusiau požeminiai)",
    5: "C1 (pusiau požeminiai apvalūs)",
    6: "C5 (pusiau požeminiai apvalūs)",
    7: "D8 (dekoratyviniai apdangalai)",
    8: "E3 (antžeminiai, pakeliamieji)",
    9: "E4 (antžeminiai, įrengti pastate, atskirame statinyje)",
    10: "F (pilnai nesukomplektuota aikštelė)",
}
ZELDINIMAS_MAP = {1: "Taip", 2: "Ne", 3: "Taip, agentūrai ES pritarus"}


class BinValues(TypedDict):
    id: int
    lat: float
    lon: float
    address: str | None
    type: str | None
    greening: str | None


@dataclass(frozen=True)
class GISSnapshot:
    bins: list[BinValues]
    retrieved: int
    skipped: int


def map_metadata(
    bin_id: int, field: str, value: object, labels: dict[int, str]
) -> str | None:
    if value is None:
        return None
    if type(value) is int and value in labels:
        return labels[value]
    logger.warning("Bin %s: unknown/unusable %s=%r; using NULL", bin_id, field, value)
    return None


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
    return {
        "id": bin_id,
        "lat": float(lat),
        "lon": float(lon),
        "address": address,
        "type": map_metadata(bin_id, "TIPAS", properties.get("TIPAS"), TIPAS_MAP),
        "greening": map_metadata(
            bin_id, "ZELDINIMAS", properties.get("ZELDINIMAS"), ZELDINIMAS_MAP
        ),
    }


def fetch_bins(source_url: str, timeout: float) -> GISSnapshot:
    bins: list[BinValues] = []
    seen: set[int] = set()
    retrieved = skipped = offset = 0
    url_parts = urlsplit(source_url)
    parameters = {
        "where": "1=1",
        "outFields": "*",
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "geojson",
        "resultRecordCount": str(PAGE_SIZE),
    }
    parameters.update(parse_qsl(url_parts.query, keep_blank_values=True))
    try:
        page_size = int(parameters["resultRecordCount"])
    except ValueError:
        raise ValueError(
            "GIS resultRecordCount must be an integer in 1..1000"
        ) from None
    if not 1 <= page_size <= PAGE_SIZE:
        raise ValueError("GIS resultRecordCount must be an integer in 1..1000")
    parameters["orderByFields"] = "OBJECTID ASC"
    while True:
        parameters["resultOffset"] = str(offset)
        query = urlencode(parameters)
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
        offset += page_size
