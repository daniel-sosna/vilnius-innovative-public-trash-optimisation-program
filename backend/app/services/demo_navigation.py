"""Read-only adapter from current demo predictions to the shared route optimizer."""
from collections import defaultdict
from math import isfinite
from time import monotonic
from typing import Protocol

import requests
from sqlalchemy import select

from app.core.config import DemoSettings
from app.infrastructure.models import Bin, Landfill, Truck
from app.interfaces.demo.schemas import Coordinate, DemoRoute, NavigationResponse, Stop, UnservedStop
from app.services.collection_plan import FILL_SHARES
from app.services.demo_prediction import DemoError, mappable, stored_bins
from app.services.demo_road_paths import RoadPaths, navigation_lock


class NavigationService(Protocol):
    def build(self, forecast_date: str, bins: list[dict], trucks: list[dict]) -> NavigationResponse: ...


class OptimizedNavigationService:
    def build(self, forecast_date: str, bins: list[dict], trucks: list[dict]) -> NavigationResponse:
        # Keep optional solver imports out of ordinary API startup.
        try:
            from app.optimization.routing import Params, Point, StopIn, TruckIn, plan_routes
        except ImportError:
            raise DemoError("optimization_unavailable", "Trūksta maršrutų optimizavimo bibliotekos. Atkurkite backend Docker atvaizdą su užrakintomis priklausomybėmis.", 503) from None

        if not navigation_lock.acquire(blocking=False):
            raise DemoError("navigation_busy", "Maršrutai jau skaičiuojami. Palaukite ir bandykite dar kartą.", 409)
        try:
            deadline = monotonic() + 14 * 60
            grouped = defaultdict(list)
            for row in sorted(bins, key=lambda item: item["bin_id"]):
                grouped[(row["waste_carrier"], row["site_id"])].append(row)
            carriers = defaultdict(list)
            unserved = []
            for (carrier, site_id), members in grouped.items():
                stop = Stop(site_id=site_id, bin_ids=[row["bin_id"] for row in members],
                            latitude=members[0]["latitude"], longitude=members[0]["longitude"])
                if any(row["capacity_m3"] is None or not isfinite(float(row["capacity_m3"])) or float(row["capacity_m3"]) <= 0 for row in members):
                    unserved.append(UnservedStop(**stop.model_dump(), reason="Trūksta tinkamos konteinerių talpos maršruto apkrovai apskaičiuoti."))
                    continue
                load = sum(float(row["capacity_m3"]) * float(FILL_SHARES[row["fill_level"]]) for row in members)
                carriers[carrier].append((stop, load))
            routes = []
            with requests.Session() as session:
                roads = RoadPaths(session, DemoSettings(), deadline)
                for carrier, entries in sorted(carriers.items(), key=lambda pair: pair[0] or ""):
                    fleet = [truck for truck in trucks if truck["waste_carrier"] == carrier] if carrier else []
                    if not fleet:
                        unserved.extend(UnservedStop(**stop.model_dump(), reason="Nėra prieinamos šio vežėjo šiukšliavežės su tinkama talpa ir sąvartyniu.") for stop, _ in entries)
                        continue
                    remaining = int(deadline - monotonic())
                    if remaining <= 0:
                        raise DemoError("routing_timeout", "Baigėsi maršrutų skaičiavimo laikas. Bandykite dar kartą.", 504)
                    depot_ids = sorted({truck["landfill_id"] for truck in fleet})
                    depots = [next(truck for truck in fleet if truck["landfill_id"] == depot_id) for depot_id in depot_ids]
                    try:
                        result = plan_routes(
                            [Point(depot["latitude"], depot["longitude"]) for depot in depots],
                            [StopIn(Point(stop.latitude, stop.longitude), load) for stop, load in entries],
                            [TruckIn(float(truck["max_volume_m3"]), depot_ids.index(truck["landfill_id"])) for truck in fleet],
                            Params(wall_limit_s=min(180, remaining)),
                        )
                    except ImportError:
                        raise DemoError("optimization_unavailable", "Trūksta maršrutų optimizavimo bibliotekos. Atkurkite backend Docker atvaizdą su užrakintomis priklausomybėmis.", 503) from None
                    except (RuntimeError, ValueError):
                        raise DemoError("optimization_failed", "Maršrutų optimizavimui nepavyko sudaryti tinkamo plano. Patikrinkite apkrovas ir parką.", 422) from None
                    for index, _ in result.unserved:
                        stop = entries[index][0]
                        unserved.append(UnservedStop(**stop.model_dump(), reason="Sustojimo apkrova viršija visų šio vežėjo šiukšliavežių talpą."))
                    for truck_index, trips in sorted(result.optimised.trips.items()):
                        if not trips:
                            continue
                        truck = fleet[truck_index]
                        depot = Coordinate(latitude=truck["latitude"], longitude=truck["longitude"])
                        waypoints, assigned, stop_indices = [depot], [], []
                        for trip in trips:
                            stops = [entries[index][0] for index in trip.stops]
                            stop_indices.extend(range(len(assigned), len(assigned) + len(stops)))
                            stop_indices.append(None)
                            waypoints.extend(stops)
                            waypoints.append(depot)
                            assigned.extend(stops)
                        path, legs = roads.driving_path(waypoints, stop_indices)
                        routes.append(DemoRoute(truck_id=truck["id"], truck_name=truck["name"],
                                                route_id=f"Plan-{truck['id']}", path=path, stops=assigned, legs=legs))
            accounted = [bin_id for route in routes for stop in route.stops for bin_id in stop.bin_ids]
            accounted.extend(bin_id for stop in unserved for bin_id in stop.bin_ids)
            if len(accounted) != len(bins) or set(accounted) != {row["bin_id"] for row in bins}:
                raise DemoError("navigation_coverage", "Optimizuoto plano konteinerių priskyrimas neatitinka prognozės.", 500)
            return NavigationResponse(forecast_date=forecast_date, routes=routes, unserved=unserved)
        finally:
            navigation_lock.release()


def navigate(forecast_date: str, bin_ids: list[int], sessions, fill_levels: dict[int, int],
             service: NavigationService | None = None) -> NavigationResponse:
    if set(fill_levels) != set(bin_ids) or any(level not in (3, 4) for level in fill_levels.values()):
        raise DemoError("navigation_predictions", "Maršrutams reikia visų pasirinktų konteinerių prognozuotų 3 arba 4 lygių.")
    with sessions() as session:
        bins = stored_bins(session, bin_ids)
        capacities = dict(session.execute(select(Bin.id, Bin.capacity_m3).where(Bin.id.in_(bin_ids))).all())
        trucks = [dict(row) for row in session.execute(
            select(Truck.id, Truck.name, Truck.waste_carrier, Truck.max_volume_m3, Truck.landfill_id,
                   Landfill.latitude, Landfill.longitude)
            .join(Landfill, Landfill.id == Truck.landfill_id)
            .where(Truck.available.is_(True), Truck.deleted.is_(False)).order_by(Truck.id)
        ).mappings()]
    if {row["bin_id"] for row in bins} != set(bin_ids):
        raise DemoError("navigation_identity", "Kai kurių konteinerių duomenų bazėje nėra. Patikrinkite prognozės registrą.")
    if any(not mappable(row) for row in bins):
        raise DemoError("navigation_coordinates", "Maršrutams reikia galiojančių visų konteinerių koordinačių.")
    for row in bins:
        row.update(capacity_m3=capacities[row["bin_id"]], fill_level=fill_levels[row["bin_id"]])
    carriers = {row["waste_carrier"] for row in bins}
    trucks = [truck for truck in trucks if truck["waste_carrier"] in carriers and mappable(truck)
              and truck["max_volume_m3"] is not None and isfinite(float(truck["max_volume_m3"]))
              and float(truck["max_volume_m3"]) > 0]
    # Keep carrier coverage when limiting a mixed fleet, without inventing vehicles.
    by_carrier = defaultdict(list)
    for truck in trucks:
        by_carrier[truck["waste_carrier"]].append(truck)
    fleet = []
    index = 0
    while len(fleet) < 150:
        batch = [members[index] for _, members in sorted(by_carrier.items(), key=lambda pair: pair[0] or "") if index < len(members)]
        if not batch:
            break
        fleet.extend(batch[:150 - len(fleet)])
        index += 1
    result = (service or OptimizedNavigationService()).build(forecast_date, bins, fleet)
    from app.services.demo_driving import remember_routes
    remember_routes(result)
    return result
