"""Deterministic demo assignments with road-following OSRM paths."""
from collections import defaultdict
from typing import Protocol
from time import monotonic

import requests

from sqlalchemy import select
from app.core.config import DemoSettings

from app.infrastructure.models import Truck
from app.interfaces.demo.schemas import DemoRoute, NavigationResponse, Stop
from app.services.demo_road_paths import RoadPaths, navigation_lock
from app.services.demo_prediction import DemoError, mappable, stored_bins


class NavigationService(Protocol):
    def build(self, forecast_date: str, bins: list[dict], trucks: list[dict]) -> NavigationResponse: ...


class RoadNavigationService:
    def build(self, forecast_date: str, bins: list[dict], trucks: list[dict]) -> NavigationResponse:
        grouped = defaultdict(list)
        for item in sorted(bins, key=lambda row: row["bin_id"]):
            grouped[item["site_id"]].append(item)
        stops = [Stop(site_id=site_id, bin_ids=[row["bin_id"] for row in members],
                      latitude=members[0]["latitude"], longitude=members[0]["longitude"])
                 for site_id, members in grouped.items()]
        stops.sort(key=lambda stop: (stop.longitude, stop.latitude, stop.site_id))
        fleet = sorted(trucks, key=lambda truck: truck["id"])[:min(150, len(stops))]
        if not fleet:
            raise DemoError("no_fleet", "Nėra prieinamų šiukšliavežių. Pridėkite arba pažymėkite jas prieinamomis.", 409)
        assignments, cursor = [], 0
        quotient, remainder = divmod(len(stops), len(fleet))
        for index, truck in enumerate(fleet):
            count = quotient + (index < remainder)
            assigned = stops[cursor:cursor + count]
            cursor += count
            assignments.append((truck, assigned))
        if not navigation_lock.acquire(blocking=False):
            raise DemoError("navigation_busy", "Maršrutai jau skaičiuojami. Palaukite ir bandykite dar kartą.", 409)
        try:
            with requests.Session() as session:
                roads = RoadPaths(session, DemoSettings(), monotonic() + 14 * 60)
                routes = [DemoRoute(
                    truck_id=truck["id"], truck_name=truck["name"], route_id=f"Demo-{truck['id']}",
                    path=roads.path(assigned), stops=assigned,
                ) for truck, assigned in assignments]
            return NavigationResponse(forecast_date=forecast_date, routes=routes)
        finally:
            navigation_lock.release()


def navigate(forecast_date: str, bin_ids: list[int], sessions,
             service: NavigationService | None = None) -> NavigationResponse:
    with sessions() as session:
        bins = stored_bins(session, bin_ids)
        trucks = [dict(row) for row in session.execute(
            select(Truck.id, Truck.name).where(Truck.available.is_(True), Truck.deleted.is_(False)).order_by(Truck.id)
        ).mappings()]
    if {row["bin_id"] for row in bins} != set(bin_ids):
        raise DemoError("navigation_identity", "Kai kurių konteinerių duomenų bazėje nėra. Patikrinkite prognozės registrą.")
    if any(not mappable(row) for row in bins):
        raise DemoError("navigation_coordinates", "Maršrutams reikia galiojančių visų konteinerių koordinačių.")
    return (service or RoadNavigationService()).build(forecast_date, bins, trucks)
