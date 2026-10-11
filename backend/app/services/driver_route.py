"""Driver route: the truck's road route from the newest planning run of the selected date."""

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.models import Bin, Site
from app.services.demo_driving import latest_routes
from app.services.trucks import TruckNotFound, get_truck


class DriverRouteError(Exception):
    def __init__(self, code: str, status: int, message: str):
        super().__init__(message)
        self.code, self.status = code, status


def forecast_date(project_date: str) -> str:
    return (date.fromisoformat(project_date) + timedelta(days=1)).isoformat()


def list_routes(project_date: str) -> list[dict]:
    """Trucks with a calculated route for the day after `project_date`, by truck ID."""
    routes = latest_routes(forecast_date(project_date))
    return [
        {
            "truck_id": route.truck_id,
            "truck_name": route.truck_name,
            "stop_count": len(route.stops),
            "bin_count": sum(len(stop.bin_ids) for stop in route.stops),
        }
        for _, route in sorted(routes.items())
    ]


def build_route(session: Session, truck_id: int, project_date: str) -> dict:
    """Return the truck's calculated road path and its service stops with every carrier bin there.

    The route comes from the newest planning run (Maršrutai) for the forecast day; landfill
    returns stay in the path but are not stops.
    """
    try:
        truck = get_truck(session, truck_id)
    except TruckNotFound:
        raise DriverRouteError("truck_not_found", 404, "Truck not found") from None
    route = latest_routes(forecast_date(project_date)).get(truck_id)
    if route is None:
        raise DriverRouteError("no_plan", 404, "No calculated route for this truck and date")

    # The legs partition the path and share their boundary vertex; a service leg ends at its stop.
    path_index: dict[int, int] = {}
    vertex = 0
    for leg in route.legs:
        vertex += len(leg.path) - 1
        if leg.stop_index is not None:
            path_index[leg.stop_index] = vertex
    if vertex != len(route.path) - 1 or sorted(path_index) != list(range(len(route.stops))):
        raise DriverRouteError("navigation_failed", 502, "The calculated route geometry is inconsistent")

    carrier = truck["waste_carrier"]
    sites = [stop.site_id for stop in route.stops]
    bins: dict[int, list] = {}
    for row in session.execute(
        select(Bin.id, Bin.site_id, Bin.inventory_number, Bin.waste_type)
        .where(Bin.site_id.in_(sites), Bin.waste_carrier == carrier)
        .order_by(Bin.id)
    ):
        bins.setdefault(row.site_id, []).append(row)
    addresses = dict(session.execute(select(Site.id, Site.address).where(Site.id.in_(sites))).all())
    known = {row.id for rows in bins.values() for row in rows}
    if any(bin_id not in known for stop in route.stops for bin_id in stop.bin_ids):
        raise DriverRouteError("bin_missing", 409, "A planned container no longer exists")

    return {
        "truck_id": truck_id,
        "plan_date": forecast_date(project_date),
        "path": [{"latitude": p.latitude, "longitude": p.longitude} for p in route.path],
        "stops": [
            {
                "site_id": stop.site_id,
                "address": addresses.get(stop.site_id),
                "path_index": path_index[index],
                "bins": [
                    {"bin_id": row.id, "inventory_number": row.inventory_number, "waste_type": row.waste_type}
                    for row in bins[stop.site_id]
                ],
            }
            for index, stop in enumerate(route.stops)
        ],
    }
