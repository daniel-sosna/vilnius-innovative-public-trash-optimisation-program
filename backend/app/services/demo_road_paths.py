"""OSRM road geometry for a supplied stop order; never substitutes straight lines."""
from math import isfinite
from threading import Lock
from time import monotonic, sleep

import requests

from app.core.config import DemoSettings
from app.interfaces.demo.schemas import Coordinate, Stop
from app.services.demo_prediction import DemoError

navigation_lock = Lock()
last_request_started = 0.0


class RoadPaths:
    def __init__(self, session: requests.Session, settings: DemoSettings, deadline: float):
        self.session, self.settings, self.deadline = session, settings, deadline

    def request(self, service: str, stops: list[Stop], **params) -> dict:
        global last_request_started
        wait = max(0, self.settings.demo_osrm_request_interval_seconds - (monotonic() - last_request_started))
        remaining = self.deadline - monotonic() - wait
        if remaining <= 0:
            raise DemoError("routing_timeout", "Baigėsi kelių maršrutų skaičiavimo laikas. Bandykite dar kartą.", 504)
        sleep(wait)
        last_request_started = monotonic()
        coordinates = ";".join(f"{stop.longitude:.7f},{stop.latitude:.7f}" for stop in stops)
        try:
            response = self.session.get(
                f"{self.settings.demo_osrm_url}/{service}/v1/driving/{coordinates}",
                params=params, timeout=(min(5, remaining), min(20, remaining)),
                headers={"User-Agent": "VipTop-Vilnius-Demo/0.1"},
            )
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError):
            raise DemoError("road_routing_unavailable", "Kelių maršrutų paslauga nepasiekiama. Patikrinkite ryšį arba DEMO_OSRM_URL ir bandykite dar kartą.", 502) from None
        if data.get("code") != "Ok":
            raise DemoError("road_route_missing", "Kelių maršruto tarp pasirinktų vietų rasti nepavyko. Patikrinkite jų koordinates.", 422)
        return data

    def path(self, stops: list[Stop]) -> list[Coordinate]:
        if len(stops) == 1:
            data = self.request("nearest", stops, number=1)
            coordinates = [data["waypoints"][0]["location"]]
        else:
            coordinates = []
            hint = ""
            # Stay within ordinary OSRM waypoint limits; overlap the chunk endpoint.
            for start in range(0, len(stops) - 1, 79):
                batch = stops[start:start + 80]
                params = dict(overview="full", geometries="geojson", steps="false", alternatives="false", continue_straight="false")
                if hint:
                    params["hints"] = ";".join([hint] + [""] * (len(batch) - 1))
                data = self.request("route", batch, **params)
                routes = data.get("routes", [])
                if not routes or routes[0].get("geometry", {}).get("type") != "LineString":
                    raise DemoError("road_geometry_invalid", "Kelių paslauga negrąžino tinkamos maršruto trajektorijos.", 502)
                part = routes[0]["geometry"].get("coordinates", [])
                if not part:
                    raise DemoError("road_geometry_invalid", "Kelių maršruto trajektorija tuščia.", 502)
                if coordinates and coordinates[-1] != part[0]:
                    raise DemoError("road_geometry_disconnected", "Kelių maršruto dalys nesusijungia. Patikrinkite sustojimo koordinates.", 502)
                coordinates.extend(part[1:] if coordinates else part)
                waypoints = data.get("waypoints", [])
                hint = waypoints[-1].get("hint", "") if waypoints else ""
        if not coordinates or any(len(point) < 2 or not all(isfinite(value) for value in point[:2]) or abs(point[0]) > 180 or abs(point[1]) > 90 for point in coordinates):
            raise DemoError("road_geometry_invalid", "Kelių paslauga grąžino netinkamas koordinates.", 502)
        return [Coordinate(longitude=point[0], latitude=point[1]) for point in coordinates]
