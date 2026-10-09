"""Bounded VASA requests and response mapping, adapted from the supplied exporter."""

import json
import logging
import math
import re
import time
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation

import mapbox_vector_tile
import requests
from app.core.config import Settings

logger = logging.getLogger(__name__)
DEFAULT_BBOX = (24.98, 54.55, 25.52, 54.85)
WASTE_TYPES = ("Mixed municipal waste", "Paper/plastic waste", "Glass waste")
GEOGRAPHICAL_FIELDS = (
    "district",
    "region",
    "sub_district",
    "city",
    "street",
    "house_number",
    "postal_code",
    "territory_type",
)
TEXT_FIELDS = (
    *GEOGRAPHICAL_FIELDS,
    "inventory_number",
    "object_group",
    "waste_carrier",
)
MAX_PAGES = 10_000


class VasaError(Exception):
    pass


def normalize_address(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).casefold()


def external_id(value) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 0 < value <= 2**63 - 1
    ):
        raise VasaError("physical bin has an invalid BIGINT identity")
    return value


def slippy(lat: float, lon: float, zoom: int) -> tuple[int, int]:
    n = 2**zoom
    lat = min(85.051128, max(-85.051128, lat))
    return min(n - 1, int((lon + 180) / 360 * n)), min(
        n - 1, int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n)
    )


def gps(local_x, local_y, z, x, y, extent):
    n = 2**z
    lon = (x + local_x / extent) / n * 360 - 180
    lat = math.degrees(
        math.atan(math.sinh(math.pi * (1 - 2 * (y + (extent - local_y) / extent) / n)))
    )
    if (
        not math.isfinite(lat)
        or not math.isfinite(lon)
        or not -90 <= lat <= 90
        or not -180 <= lon <= 180
    ):
        raise VasaError("invalid point coordinates")
    return lat, lon


def collection_tiles(bbox, zoom):
    west, south, east, north = bbox
    x1, y1 = slippy(north, west, zoom)
    x2, y2 = slippy(south, east, zoom)
    # This generator deliberately does not build a citywide tile/future list.
    for x in range(x1, x2 + 1):
        for y in range(y1, y2 + 1):
            yield zoom, x, y


def within(bbox, latitude, longitude):
    west, south, east, north = bbox
    return west <= longitude <= east and south <= latitude <= north


def count_client_addresses(value):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            logger.warning("Malformed client_addresses; count remains NULL")
            return None
    if value is not None and not isinstance(value, list):
        logger.warning("Malformed client_addresses; count remains NULL")
    return len(value) if isinstance(value, list) else None


def optional_text(value, field):
    if value is None or isinstance(value, str):
        return value
    logger.warning("Malformed optional %s; storing NULL", field)
    return None


def map_bin(properties, latitude, longitude):
    identity = external_id(properties.get("id"))
    waste_type = properties.get("dumpster_type")
    if not isinstance(waste_type, str) or not waste_type:
        raise VasaError(f"bin={identity}: missing waste type")
    values = {name: optional_text(properties.get(name), name) for name in TEXT_FIELDS}
    volume = properties.get("volume")
    capacity = None
    if volume is not None:
        try:
            if isinstance(volume, bool):
                raise InvalidOperation
            parsed = Decimal(str(volume))
            if not parsed.is_finite():
                raise InvalidOperation
            capacity = str(parsed)
        except (InvalidOperation, ValueError):
            logger.warning("bin=%s: malformed volume; capacity remains NULL", identity)
    return dict(
        values,
        external_id=identity,
        waste_type=waste_type,
        capacity_m3=capacity,
        latitude=latitude,
        longitude=longitude,
        client_count=count_client_addresses(properties.get("client_addresses")),
    )


def eligible(values, bbox):
    group = normalize_address(values.get("object_group") or "")
    city = (values.get("city") or "").casefold()
    return (
        values["waste_type"] in WASTE_TYPES
        and group != "individualios valdos"
        and (not city or "vilniaus" in city)
        and within(bbox, values["latitude"], values["longitude"])
    )


def site_identity(values):
    address = " ".join(
        (values.get(name) or "").strip() for name in ("street", "house_number")
    ).strip()
    address = re.sub(r"\s+", " ", address)
    if address:
        return "address:" + normalize_address(address), address
    identity = values["external_id"]
    logger.warning("bin=%s: missing registered address", identity)
    return f"unknown:{identity}", f"Unknown address ({identity})"


@dataclass
class TileResponse:
    candidates: list[dict]
    errors: list[str]
    physical_count: int


@dataclass
class HistoryPage:
    events: list[dict]
    errors: list[str]
    last_page: int | None
    next_page: int | None
    pagination: dict


def parse_tile(content: bytes, tile, bbox) -> TileResponse:
    try:
        layers = mapbox_vector_tile.decode(content)
        if "vasa_containers" not in layers:
            raise ValueError("missing vasa_containers layer")
        candidates, errors, physical, aggregates = [], [], 0, 0
        for layer in layers.values():
            extent = layer.get("extent")
            if isinstance(extent, bool) or not isinstance(extent, int) or extent <= 0:
                raise ValueError("invalid layer extent")
            for feature in layer.get("features", []):
                properties = feature.get("properties", {})
                geometry = feature.get("geometry", {})
                waste = properties.get("dumpster_type")
                group = properties.get("object_group")
                city = properties.get("city")
                if (
                    (isinstance(waste, str) and waste not in WASTE_TYPES)
                    or (
                        isinstance(group, str)
                        and normalize_address(group) == "individualios valdos"
                    )
                    or (
                        isinstance(city, str)
                        and city
                        and "vilniaus" not in city.casefold()
                    )
                ):
                    continue
                if "cluster_id" in properties or "point_count" in properties:
                    aggregates += 1
                    continue
                if geometry.get("type") != "Point":
                    if properties.get("id") is not None and properties.get(
                        "dumpster_type"
                    ):
                        errors.append("physical bin has non-point geometry")
                    else:
                        aggregates += 1
                    continue
                try:
                    identity = external_id(properties.get("id"))
                    physical += 1
                    point = geometry.get("coordinates")
                    if (
                        not isinstance(point, (list, tuple))
                        or len(point) != 2
                        or any(
                            isinstance(v, bool)
                            or not isinstance(v, (int, float))
                            or not math.isfinite(v)
                            for v in point
                        )
                    ):
                        raise VasaError(f"bin={identity}: invalid tile point")
                    lat, lon = gps(*point, *tile, extent)
                    if not within(bbox, lat, lon):
                        continue
                    # Resolve missing requested metadata before applying source filters.
                    candidates.append(
                        {
                            "properties": properties,
                            "latitude": lat,
                            "longitude": lon,
                            "tile": list(tile),
                            "needs_detail": any(
                                key not in properties for key in GEOGRAPHICAL_FIELDS
                            ),
                        }
                    )
                except VasaError as error:
                    errors.append(str(error))
        if aggregates:
            errors.append(
                "aggregate features prevent complete physical-bin coverage at this zoom"
            )
        return TileResponse(candidates, errors, physical)
    except (ValueError, KeyError, TypeError, OverflowError) as error:
        raise VasaError(
            f"tile={tile}: malformed MVT ({type(error).__name__})"
        ) from error


def valid_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    if isinstance(value, str) and value.casefold() in ("true", "false"):
        return value.casefold() == "true"
    raise ValueError("invalid service status")


def parse_history(payload, page):
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise VasaError("history response lacks a data array")
    meta = payload.get("meta", {})
    links = payload.get("links", {})
    if not isinstance(meta, dict) or not isinstance(links, dict):
        raise VasaError("invalid pagination metadata")
    current = meta.get("current_page", page)
    last = meta.get("last_page")
    if isinstance(current, bool) or not isinstance(current, int) or current != page:
        raise VasaError("unexpected current_page")
    if last is not None and (
        isinstance(last, bool)
        or not isinstance(last, int)
        or not 1 <= last <= MAX_PAGES
    ):
        raise VasaError("invalid last_page")
    if last is None and "next" not in links:
        raise VasaError("missing continuation metadata")
    pagination = {
        key: meta[key] for key in ("last_page", "per_page", "total") if key in meta
    }
    for key in ("per_page", "total"):
        if key in pagination and (
            isinstance(pagination[key], bool)
            or not isinstance(pagination[key], int)
            or pagination[key] < (1 if key == "per_page" else 0)
        ):
            raise VasaError(f"invalid {key}")
    continuation = page < last if last is not None else bool(links["next"])
    if continuation and page >= MAX_PAGES:
        raise VasaError("pagination sanity limit exceeded")
    events, errors = {}, []
    for index, item in enumerate(payload["data"]):
        try:
            if not isinstance(item, dict) or not isinstance(
                item.get("service_date"), str
            ):
                raise ValueError("missing timestamp")
            date = datetime.fromisoformat(item["service_date"])
            if date.tzinfo is not None:
                raise ValueError(
                    "offset-bearing timestamp; expected naive wall-clock time"
                )
            status = valid_bool(item.get("is_serviced"))
            reason = item.get("non_serviced_reason")
            if reason is not None and not isinstance(reason, str):
                raise ValueError("invalid reason")
            key = date, status
            row = {
                "date": date,
                "was_serviced": status,
                "non_serviced_reason": reason,
                "fill_level": None,
            }
            if key not in events or (reason and not events[key]["non_serviced_reason"]):
                events[key] = row
        except (ValueError, TypeError) as error:
            errors.append(f"event={index}: {error}")
    return HistoryPage(
        list(events.values()),
        errors,
        last,
        page + 1 if continuation else None,
        pagination,
    )


class VasaClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    def _get(self, template, accept, params=None, **keys):
        url = template.format(**keys)
        for attempt in range(5):
            try:
                response = requests.get(
                    url,
                    params=params,
                    timeout=self.settings.bin_sync_http_timeout_seconds,
                    headers={"Accept": accept, "User-Agent": "Mozilla/5.0"},
                    allow_redirects=False,
                )
                if response.status_code == 429 or response.status_code >= 500:
                    raise requests.HTTPError(f"temporary HTTP {response.status_code}")
                if response.status_code != 200:
                    raise VasaError(f"request returned HTTP {response.status_code}")
                return response
            except requests.RequestException as error:
                if attempt == 4:
                    raise VasaError(
                        f"request exhausted five attempts ({type(error).__name__})"
                    ) from error
                time.sleep(min(20, 2**attempt))
        raise AssertionError("unreachable")

    def tile(self, tile, bbox):
        z, x, y = tile
        response = self._get(
            self.settings.vasa_tile_url_template,
            "application/x-protobuf",
            {"dumpster_type": json.dumps(WASTE_TYPES)},
            z=z,
            x=x,
            y=y,
        )
        return parse_tile(response.content, tile, bbox)

    def detail(self, identity):
        response = self._get(
            self.settings.vasa_bin_url_template,
            "application/json",
            external_id=identity,
        )
        try:
            payload = response.json()
            if (
                not isinstance(payload, dict)
                or external_id(payload.get("id")) != identity
            ):
                raise VasaError("detail identity does not match requested bin")
            return payload
        except ValueError as error:
            raise VasaError("malformed detail JSON") from error

    def history(self, identity, page):
        response = self._get(
            self.settings.vasa_history_url_template,
            "application/json",
            {"page": page},
            external_id=identity,
        )
        try:
            return parse_history(response.json(), page)
        except ValueError as error:
            raise VasaError("malformed history JSON") from error
