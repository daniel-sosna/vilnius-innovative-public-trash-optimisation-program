"""Navigation interface for the Driver screen, with a fixed-path mock implementation.

A real router replaces `MockNavigationService` by changing `get_navigation_service`.
"""

import json
from dataclasses import dataclass
from functools import lru_cache
from math import isfinite
from pathlib import Path
from typing import Protocol

ROAD_PATH_FILE = Path(__file__).parent / "data" / "driver_road_path.geojson"


class NavigationError(Exception):
    pass


@dataclass(frozen=True)
class StopIn:
    site_id: int
    latitude: float
    longitude: float


@dataclass(frozen=True)
class NavigationResult:
    path: list[tuple[float, float]]  # (latitude, longitude), ordered along the road
    stop_index: list[int]  # path vertex of each input stop, in input order


class NavigationService(Protocol):
    def build(self, stops: list[StopIn]) -> NavigationResult: ...


def validate_result(result: NavigationResult, stop_count: int) -> NavigationResult:
    path = result.path
    if len(path) < 2 or any(
        not (isfinite(lat) and isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180)
        for lat, lon in path
    ):
        raise NavigationError("Navigation returned an invalid road path")
    index = result.stop_index
    if (
        len(index) != stop_count
        or any(not 0 <= value < len(path) for value in index)
        or any(b <= a for a, b in zip(index, index[1:]))
    ):
        raise NavigationError("Navigation returned invalid stop positions")
    return result


@lru_cache(maxsize=1)
def _mock_path() -> tuple[tuple[float, float], ...]:
    try:
        with ROAD_PATH_FILE.open(encoding="utf-8") as file:
            coordinates = json.load(file)["features"][0]["geometry"]["coordinates"]
        return tuple((float(lat), float(lon)) for lon, lat in coordinates)
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        raise NavigationError("Mock road path is unavailable") from None


class MockNavigationService:
    """Fixed real-road path; stops are spaced evenly along it and ignore their coordinates."""

    def build(self, stops: list[StopIn]) -> NavigationResult:
        path = list(_mock_path())
        count = len(stops)
        if count < 1 or count > len(path) - 1:
            raise NavigationError("The road path cannot hold this number of stops")
        last = len(path) - 1
        index = [round((position + 1) * last / count) for position in range(count)]
        return validate_result(NavigationResult(path=path, stop_index=index), count)


def get_navigation_service() -> NavigationService:
    return MockNavigationService()
