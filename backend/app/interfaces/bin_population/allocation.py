"""Resident allocation from the population-density grid. No database access.

Residents of every populated polygon go to the nearest residential collection point
of each waste type; a point splits them among its bins by capacity. Geometry is plain
Python: ray casting, shoelace centroids and an equirectangular distance.
"""

import json
import math
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_SUPPRESSED_DENSITY = 5
MAX_SUPPRESSED_DENSITY = 10
SUPPRESSED_VALUE = "<11"

RESIDENTIAL_GROUPS = frozenset(
    {
        "Daugiabučiai namai",
        "Dvibučiai",
        "Daugiabučių/garažų bendrijos",
        "Sodų bendrijos",
        "Sodų/garažų bendrijos",
    }
)

# Equirectangular projection around Vilnius (54.7 N); error below 0.5% across the city.
METRES_PER_DEGREE = 111_320.0
LON_SCALE = math.cos(math.radians(54.7)) * METRES_PER_DEGREE
POLYGON_GRID_DEGREES = 0.01
POINT_GRID_METRES = 500.0


class DensityFileError(ValueError):
    """The density file is unreadable or a feature is invalid."""


@dataclass
class PopulationPolygon:
    id: int
    density_per_ha: int | None
    suppressed: bool
    area_ha: float
    residents: float
    bbox: tuple[float, float, float, float]  # min_lon, min_lat, max_lon, max_lat
    rings: list  # GeoJSON coordinates: outer ring first, then holes
    centroid: tuple[float, float] | None  # (lon, lat); None when residents == 0


@dataclass
class BinRecord:
    id: int
    waste_type: str
    capacity_m3: float | None
    latitude: float
    longitude: float
    object_group: str | None


@dataclass
class WasteTypeStats:
    waste_type: str
    residential_bins: int = 0
    points: int = 0
    allocated: float = 0.0
    unallocated: float = 0.0
    distances: list[float] = field(default_factory=list)
    factors: list[float] = field(default_factory=list)  # residential bins only


@dataclass
class Allocation:
    cell_by_bin: dict[int, int | None]
    factor_by_bin: dict[int, float]
    stats: dict[str, WasteTypeStats]


def project(lon: float, lat: float) -> tuple[float, float]:
    return lon * LON_SCALE, lat * METRES_PER_DEGREE


def ring_centroid(ring: list) -> tuple[float, float]:
    """Area-weighted centroid of a ring (shoelace); vertex mean for a degenerate ring."""
    area2 = cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(ring, ring[1:]):
        cross = x0 * y1 - x1 * y0
        area2 += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    if abs(area2) < 1e-18:
        return (
            sum(p[0] for p in ring) / len(ring),
            sum(p[1] for p in ring) / len(ring),
        )
    return cx / (3 * area2), cy / (3 * area2)


def parse_polygons(path: Path, suppressed_density: float) -> list[PopulationPolygon]:
    """Read and validate the GeoJSON FeatureCollection."""
    try:
        with open(path, encoding="utf-8") as file:
            collection = json.load(file)
    except FileNotFoundError:
        raise DensityFileError(f"density file not found: {path}") from None
    except (OSError, ValueError) as error:
        raise DensityFileError(f"cannot read density file {path}: {error}") from None
    features = collection.get("features") if isinstance(collection, dict) else None
    if not isinstance(features, list):
        raise DensityFileError(f"{path} is not a GeoJSON FeatureCollection")
    polygons: list[PopulationPolygon] = []
    seen: set[int] = set()
    for index, feature in enumerate(features):
        properties = feature.get("properties") or {}
        object_id = properties.get("OBJECTID")
        name = f"feature #{index} (OBJECTID {object_id!r})"
        if not isinstance(object_id, int) or isinstance(object_id, bool):
            raise DensityFileError(f"{name} has no integer OBJECTID")
        if object_id in seen:
            raise DensityFileError(f"{name} repeats an OBJECTID")
        seen.add(object_id)
        geometry = feature.get("geometry") or {}
        if geometry.get("type") != "Polygon" or not geometry.get("coordinates"):
            raise DensityFileError(f"{name} is not a Polygon")
        rings = geometry["coordinates"]
        raw = properties.get("gyv_sk_1ha")
        if raw is None:
            density, suppressed, per_ha = None, False, 0.0
        elif raw == SUPPRESSED_VALUE:
            density, suppressed, per_ha = None, True, float(suppressed_density)
        elif isinstance(raw, str) and raw.isascii() and raw.isdigit():
            density, suppressed, per_ha = int(raw), False, float(raw)
        else:
            raise DensityFileError(
                f"{name} has density {raw!r}, expected a whole number, "
                f'"{SUPPRESSED_VALUE}" or null'
            )
        area = properties.get("Shape_Area")
        if not isinstance(area, (int, float)) or area < 0:
            raise DensityFileError(f"{name} has no valid Shape_Area")
        area_ha = area / 10_000
        residents = per_ha * area_ha
        outer = rings[0]
        xs = [p[0] for p in outer]
        ys = [p[1] for p in outer]
        polygons.append(
            PopulationPolygon(
                id=object_id,
                density_per_ha=density,
                suppressed=suppressed,
                area_ha=area_ha,
                residents=residents,
                bbox=(min(xs), min(ys), max(xs), max(ys)),
                rings=rings,
                centroid=ring_centroid(outer) if residents > 0 else None,
            )
        )
    return polygons


def in_ring(lon: float, lat: float, ring: list) -> bool:
    inside = False
    for (x0, y0), (x1, y1) in zip(ring, ring[1:]):
        if (y0 > lat) != (y1 > lat) and lon < (x1 - x0) * (lat - y0) / (y1 - y0) + x0:
            inside = not inside
    return inside


def in_polygon(lon: float, lat: float, rings: list) -> bool:
    """Ray casting on the outer ring, excluding holes."""
    if not in_ring(lon, lat, rings[0]):
        return False
    return not any(in_ring(lon, lat, hole) for hole in rings[1:])


class PolygonIndex:
    """Uniform grid over polygon bounding boxes."""

    def __init__(self, polygons: list[PopulationPolygon]):
        self.cells: dict[tuple[int, int], list[PopulationPolygon]] = defaultdict(list)
        step = POLYGON_GRID_DEGREES
        for polygon in sorted(polygons, key=lambda p: p.id):
            min_lon, min_lat, max_lon, max_lat = polygon.bbox
            for i in range(math.floor(min_lon / step), math.floor(max_lon / step) + 1):
                for j in range(math.floor(min_lat / step), math.floor(max_lat / step) + 1):
                    self.cells[(i, j)].append(polygon)

    def find(self, lon: float, lat: float) -> int | None:
        """Id of the containing polygon (lowest id on shared edges), or None."""
        key = (
            math.floor(lon / POLYGON_GRID_DEGREES),
            math.floor(lat / POLYGON_GRID_DEGREES),
        )
        # Candidates are stored in id order, so the first match is the lowest id.
        for polygon in self.cells.get(key, ()):
            min_lon, min_lat, max_lon, max_lat = polygon.bbox
            if min_lon <= lon <= max_lon and min_lat <= lat <= max_lat:
                if in_polygon(lon, lat, polygon.rings):
                    return polygon.id
        return None


@dataclass
class CollectionPoint:
    x: float
    y: float
    bins: list[BinRecord]
    capacity: float
    min_bin_id: int
    residents: float = 0.0


class PointIndex:
    """Grid of collection points searched in growing rings."""

    def __init__(self, points: list[CollectionPoint]):
        self.cells: dict[tuple[int, int], list[CollectionPoint]] = defaultdict(list)
        for point in points:
            self.cells[self._key(point.x, point.y)].append(point)
        self.max_ring = 1
        if self.cells:
            keys = list(self.cells)
            span_i = max(k[0] for k in keys) - min(k[0] for k in keys)
            span_j = max(k[1] for k in keys) - min(k[1] for k in keys)
            self.max_ring = max(span_i, span_j) + 1

    @staticmethod
    def _key(x: float, y: float) -> tuple[int, int]:
        return math.floor(x / POINT_GRID_METRES), math.floor(y / POINT_GRID_METRES)

    def nearest(self, x: float, y: float) -> tuple[CollectionPoint, float]:
        ci, cj = self._key(x, y)
        best: tuple[float, int, CollectionPoint] | None = None
        ring = 0
        while True:
            for i in range(ci - ring, ci + ring + 1):
                for j in range(cj - ring, cj + ring + 1):
                    if max(abs(i - ci), abs(j - cj)) != ring:
                        continue
                    for point in self.cells.get((i, j), ()):
                        distance = math.hypot(point.x - x, point.y - y)
                        candidate = (distance, point.min_bin_id, point)
                        if best is None or candidate[:2] < best[:2]:
                            best = candidate
            # Points in ring r+1 and beyond are at least r * cell size away.
            if best is not None and best[0] <= ring * POINT_GRID_METRES:
                return best[2], best[0]
            ring += 1
            if ring > self.max_ring + 2 and best is not None:
                return best[2], best[0]


def is_residential(record: BinRecord) -> bool:
    return (
        record.object_group in RESIDENTIAL_GROUPS
        and record.capacity_m3 is not None
        and record.capacity_m3 > 0
    )


def allocate(bins: list[BinRecord], polygons: list[PopulationPolygon]) -> Allocation:
    index = PolygonIndex(polygons)
    cell_by_bin = {b.id: index.find(b.longitude, b.latitude) for b in bins}
    factor_by_bin = {b.id: 0.0 for b in bins}
    total_residents = sum(p.residents for p in polygons)
    sources = [(p, project(*p.centroid)) for p in polygons if p.centroid and p.residents > 0]

    by_type: dict[str, list[BinRecord]] = defaultdict(list)
    for record in bins:
        by_type[record.waste_type].append(record)

    stats: dict[str, WasteTypeStats] = {}
    for waste_type in sorted(by_type):
        type_stats = WasteTypeStats(waste_type)
        stats[waste_type] = type_stats
        grouped: dict[tuple[float, float], list[BinRecord]] = defaultdict(list)
        for record in by_type[waste_type]:
            if is_residential(record):
                grouped[(record.latitude, record.longitude)].append(record)
        type_stats.residential_bins = sum(len(g) for g in grouped.values())
        type_stats.points = len(grouped)
        if not grouped:
            type_stats.unallocated = total_residents
            continue
        points = []
        for (lat, lon), members in grouped.items():
            x, y = project(lon, lat)
            points.append(
                CollectionPoint(
                    x, y, members,
                    capacity=sum(float(m.capacity_m3) for m in members),
                    min_bin_id=min(m.id for m in members),
                )
            )
        point_index = PointIndex(points)
        for polygon, (x, y) in sources:
            point, distance = point_index.nearest(x, y)
            point.residents += polygon.residents
            type_stats.allocated += polygon.residents
            type_stats.distances.append(distance)
        for point in points:
            for member in point.bins:
                factor = point.residents * float(member.capacity_m3) / point.capacity
                factor_by_bin[member.id] = factor
                type_stats.factors.append(factor)
    return Allocation(cell_by_bin, factor_by_bin, stats)


def percentile(values: list[float], fraction: float) -> float:
    """Linear-interpolated percentile of unsorted values; 0 when empty."""
    if not values:
        return 0.0
    ordered = sorted(values)
    position = fraction * (len(ordered) - 1)
    low = math.floor(position)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)
