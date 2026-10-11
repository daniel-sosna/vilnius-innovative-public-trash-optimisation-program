"""Driver route: stop order from the stored route plan, bins from the collection plan."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.models import Bin
from app.services.collection_plan import get_plan
from app.services.navigation import (
    NavigationError,
    NavigationService,
    StopIn,
    get_navigation_service,
)
from app.services.route_plan import get_stored_plan
from app.services.trucks import TruckNotFound, get_truck

# Placeholder until the date selector exists: the plan date (T+1) the Driver follows.
DRIVER_PLAN_DATE = date(2026, 9, 16)


class DriverRouteError(Exception):
    def __init__(self, code: str, status: int, message: str):
        super().__init__(message)
        self.code, self.status = code, status


def build_route(
    session: Session, truck_id: int, navigation: NavigationService | None = None
) -> dict:
    """Return the truck's first stored trip as stops with all the carrier's bins and a road path.

    `stops` is empty (and `path` too) when none of the trip's stops is in the collection plan.
    """
    try:
        truck = get_truck(session, truck_id)
    except TruckNotFound:
        raise DriverRouteError("truck_not_found", 404, "Truck not found") from None
    carrier = truck["waste_carrier"]
    plan = get_stored_plan(session, DRIVER_PLAN_DATE, carrier)
    planned = next((t for t in plan["trucks"] if t["truck_id"] == truck_id), None) if plan else None
    if planned is None or not planned["trips"]:
        raise DriverRouteError("no_plan", 404, "No stored route for this truck and date")

    sites = {stop["site_id"]: stop for stop in get_plan(session, DRIVER_PLAN_DATE, [carrier])[carrier]}
    trip_stops = [stop for stop in planned["trips"][0]["stops"] if stop["site_id"] in sites]
    result = {"truck_id": truck_id, "plan_date": DRIVER_PLAN_DATE, "path": [], "stops": []}
    if not trip_stops:
        return result

    bin_ids = [b["bin_id"] for stop in trip_stops for b in sites[stop["site_id"]]["bins"]]
    details = {
        row.id: row
        for row in session.execute(
            select(Bin.id, Bin.inventory_number, Bin.waste_type).where(Bin.id.in_(bin_ids))
        )
    }
    if len(details) != len(set(bin_ids)):
        raise DriverRouteError("bin_missing", 409, "A planned container no longer exists")

    try:
        navigation_result = (navigation or get_navigation_service()).build(
            [StopIn(s["site_id"], s["latitude"], s["longitude"]) for s in trip_stops]
        )
    except NavigationError:
        raise DriverRouteError("navigation_failed", 502, "Navigation is unavailable") from None

    result["path"] = [
        {"latitude": lat, "longitude": lon} for lat, lon in navigation_result.path
    ]
    result["stops"] = [
        {
            "site_id": stop["site_id"],
            "address": stop["address"],
            "path_index": path_index,
            "bins": [
                {
                    "bin_id": b["bin_id"],
                    "inventory_number": details[b["bin_id"]].inventory_number,
                    "waste_type": details[b["bin_id"]].waste_type,
                }
                for b in sites[stop["site_id"]]["bins"]
            ],
        }
        for stop, path_index in zip(trip_stops, navigation_result.stop_index)
    ]
    return result
