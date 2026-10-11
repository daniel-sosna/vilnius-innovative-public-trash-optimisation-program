"""Road geometry for the shared driving illustration; no collection writes."""
from time import monotonic
from math import cos, isfinite, radians

import requests

from app.core.config import DemoSettings
from app.interfaces.demo.schemas import Coordinate, DrivingLeg, DrivingRouteResponse, Stop
from app.services.demo_prediction import DemoError
from app.services.demo_road_paths import RoadPaths, navigation_lock

# Fixed illustration locations, not database bin identities or saved routes.
DRIVING_STOPS = [
    # Western roundabout arc at Geležinio Vilko / A. Goštauto, snapped by OSRM.
    (25.2610, 54.6937), (25.2655, 54.6952), (25.2692, 54.6938),
    (25.2724, 54.6919), (25.2759, 54.6908), (25.2785, 54.6889),
]


def driving_route() -> DrivingRouteResponse:
    if not navigation_lock.acquire(blocking=False):
        raise DemoError("navigation_busy", "Kelių maršrutai jau skaičiuojami. Palaukite ir atnaujinkite puslapį.", 409)
    try:
        stops = [Stop(site_id=index, bin_ids=[], longitude=lon, latitude=lat)
                 for index, (lon, lat) in enumerate(DRIVING_STOPS)]
        with requests.Session() as session:
            roads = RoadPaths(session, DemoSettings(), monotonic() + 45)
            data = roads.request("route", stops, overview="full", geometries="geojson",
                                 steps="false", alternatives="false", continue_straight="false")
        routes = data.get("routes", [])
        if not routes or len(routes[0].get("legs", [])) != len(stops) - 1:
            raise DemoError("driving_geometry_invalid", "Nepavyko gauti šiukšliavežės kelio trajektorijos. Atnaujinkite puslapį.", 502)
        geometry = routes[0].get("geometry", {})
        points = geometry.get("coordinates", [])
        waypoints = data.get("waypoints", [])
        if (geometry.get("type") != "LineString" or len(points) < 2
                or len(waypoints) != len(stops)
                or any(len(point) < 2 or not all(isfinite(value) for value in point[:2])
                       or abs(point[0]) > 180 or abs(point[1]) > 90 for point in points)):
            raise DemoError("driving_geometry_invalid", "Kelių paslauga grąžino netinkamą trajektoriją.", 502)
        whole = [Coordinate(longitude=point[0], latitude=point[1]) for point in points]
        legs, cursor = [], 0
        # Use the continuous route overview as the sole geometry authority.
        # Adjacent legs share a vertex rather than requiring independently
        # generated maneuver endpoints to match exactly.
        for index, leg in enumerate(routes[0]["legs"]):
            if index == len(stops) - 2:
                end = len(whole) - 1
            else:
                lon, lat = waypoints[index + 1]["location"]
                scale = cos(radians(lat))
                end = min(range(cursor, len(whole)), key=lambda vertex: (
                    ((whole[vertex].longitude - lon) * scale) ** 2
                    + (whole[vertex].latitude - lat) ** 2
                ))
            legs.append(DrivingLeg(path=whole[cursor:end + 1], distance_m=leg["distance"]))
            cursor = end
        return DrivingRouteResponse(path=whole, stops=[leg.path[-1] for leg in legs], legs=legs)
    finally:
        navigation_lock.release()
