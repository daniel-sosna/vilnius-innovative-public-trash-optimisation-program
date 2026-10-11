from datetime import date
from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.infrastructure.models import (
    CollectionStop,
    Landfill,
    RoutePlan,
    RouteStop,
    RouteTrip,
    RouteTruck,
    Truck,
)
from app.optimization.routing import (
    Params,
    Point,
    Result,
    StopIn,
    TruckIn,
    params_dict,
    plan_routes,
)
from app.services.collection_plan import get_plan


class NoCollectionPlan(Exception):
    pass


class NothingToPlan(Exception):
    pass


class NoEligibleTruck(Exception):
    pass


def _figures(figures) -> dict:
    return {
        "distance_km": round(figures.distance_km, 3),
        "trips": figures.trips,
        "trucks_used": figures.trucks_used,
        "overtime_min": round(figures.overtime_min, 1),
        "stops_served": figures.stops_served,
    }


def compute_plan(session: Session, day: date, carrier: str, params: Params) -> dict:
    """Plan the routes of `carrier` for `day` and replace the stored plan in one transaction.

    Reads the due stops of the collection plan and the carrier's trucks that are available,
    not deleted and have a landfill with coordinates. The solve runs between the read and
    the write, with no transaction open. Returns the stored summary.
    """
    if not session.scalar(select(func.count()).select_from(CollectionStop).where(CollectionStop.date == day)):
        raise NoCollectionPlan
    stops = get_plan(session, day, [carrier])[carrier]
    if not stops:
        raise NothingToPlan
    rows = session.execute(
        select(Truck, Landfill)
        .outerjoin(Landfill, Landfill.id == Truck.landfill_id)
        .where(Truck.waste_carrier == carrier, Truck.available.is_(True), Truck.deleted.is_(False))
        .order_by(Truck.id)
    ).all()
    eligible = [
        (truck, landfill)
        for truck, landfill in rows
        if landfill is not None and landfill.latitude is not None and landfill.longitude is not None
    ]
    excluded = len(rows) - len(eligible)
    if not eligible:
        raise NoEligibleTruck
    landfills = {landfill.id: landfill for _, landfill in eligible}
    depot_ids = sorted(landfills)
    depots = [Point(landfills[i].latitude, landfills[i].longitude) for i in depot_ids]
    stop_inputs = [
        StopIn(Point(float(s["latitude"]), float(s["longitude"])), float(s["overall_predicted_fill_m3"]))
        for s in stops
    ]
    truck_inputs = [
        TruckIn(float(truck.max_volume_m3), depot_ids.index(truck.landfill_id)) for truck, _ in eligible
    ]
    # Plain copies: the ORM objects expire when the read transaction ends.
    truck_snapshots = [
        (
            truck.id,
            truck.name,
            truck.max_volume_m3,
            {"id": landfill.id, "name": landfill.name, "latitude": landfill.latitude, "longitude": landfill.longitude},
        )
        for truck, landfill in eligible
    ]
    session.rollback()  # no transaction while solving
    result = plan_routes(depots, stop_inputs, truck_inputs, params)
    return _store(session, day, carrier, params, stops, truck_snapshots, excluded, result)


def _store(session, day, carrier, params, stops, trucks, excluded, result: Result) -> dict:
    summary = {
        "optimised": _figures(result.optimised.figures),
        "baseline": _figures(result.baseline.figures),
        "saved_km": round(result.saved_km, 3),
        "saved_percent": round(result.saved_percent, 2),
        "unserved_stops": len(result.unserved),
        "stops_total": len(stops),
        "iterations": result.iterations,
        "stopped_by_wall_limit": result.stopped_by_wall_limit,
        "solve_seconds": round(result.solve_seconds, 1),
    }
    unserved = [
        {
            "site_id": stops[i]["site_id"],
            "address": stops[i]["address"],
            "latitude": stops[i]["latitude"],
            "longitude": stops[i]["longitude"],
            "load_m3": float(stops[i]["overall_predicted_fill_m3"]),
            "reason": reason,
        }
        for i, reason in result.unserved
    ]
    session.execute(
        delete(RoutePlan).where(RoutePlan.date == day, RoutePlan.waste_carrier == carrier)
    )
    plan = RoutePlan(
        date=day,
        waste_carrier=carrier,
        parameters=params_dict(params),
        summary=summary,
        unserved=unserved,
        excluded_trucks=excluded,
    )
    session.add(plan)
    session.flush()
    for position, (truck_id, name, capacity, landfill) in enumerate(trucks):
        route_truck = RouteTruck(
            plan_id=plan.id,
            position=position,
            truck_id=truck_id,
            name=name,
            max_volume_m3=capacity,
            landfill_id=landfill["id"],
            landfill_name=landfill["name"],
            landfill_latitude=landfill["latitude"],
            landfill_longitude=landfill["longitude"],
        )
        session.add(route_truck)
        session.flush()
        for seq, trip in enumerate(result.optimised.trips.get(position, [])):
            route_trip = RouteTrip(
                route_truck_id=route_truck.id,
                seq=seq,
                load_m3=Decimal(str(round(trip.load_m3, 3))),
                distance_km=Decimal(str(round(trip.distance_m / 1000, 3))),
                duration_min=Decimal(str(round(trip.duration_s / 60, 1))),
            )
            session.add(route_trip)
            session.flush()
            for stop_seq, index in enumerate(trip.stops):
                stop = stops[index]
                session.add(
                    RouteStop(
                        trip_id=route_trip.id,
                        seq=stop_seq,
                        site_id=stop["site_id"],
                        address=stop["address"],
                        latitude=stop["latitude"],
                        longitude=stop["longitude"],
                        load_m3=stop["overall_predicted_fill_m3"],
                        bin_count=len(stop["bins"]),
                    )
                )
    session.commit()
    return {"id": plan.id, "excluded_trucks": excluded, "parameters": params_dict(params), **summary}


def get_stored_plan(session: Session, day: date, carrier: str) -> dict | None:
    """Return the stored plan of `carrier` and `day`, or None. Trips and stops are in order."""
    plan = session.scalar(
        select(RoutePlan).where(RoutePlan.date == day, RoutePlan.waste_carrier == carrier)
    )
    if plan is None:
        return None
    trucks = session.scalars(
        select(RouteTruck).where(RouteTruck.plan_id == plan.id).order_by(RouteTruck.position)
    ).all()
    trips = session.scalars(
        select(RouteTrip)
        .join(RouteTruck, RouteTruck.id == RouteTrip.route_truck_id)
        .where(RouteTruck.plan_id == plan.id)
        .order_by(RouteTrip.route_truck_id, RouteTrip.seq)
    ).all()
    stops_by_trip: dict[int, list[RouteStop]] = {}
    for stop in session.scalars(
        select(RouteStop)
        .join(RouteTrip, RouteTrip.id == RouteStop.trip_id)
        .join(RouteTruck, RouteTruck.id == RouteTrip.route_truck_id)
        .where(RouteTruck.plan_id == plan.id)
        .order_by(RouteStop.trip_id, RouteStop.seq)
    ):
        stops_by_trip.setdefault(stop.trip_id, []).append(stop)
    trips_by_truck: dict[int, list[dict]] = {}
    for trip in trips:
        trips_by_truck.setdefault(trip.route_truck_id, []).append(
            {
                "load_m3": float(trip.load_m3),
                "distance_km": float(trip.distance_km),
                "duration_min": float(trip.duration_min),
                "stops": [
                    {
                        "site_id": s.site_id,
                        "address": s.address,
                        "latitude": s.latitude,
                        "longitude": s.longitude,
                        "load_m3": float(s.load_m3),
                        "bin_count": s.bin_count,
                    }
                    for s in stops_by_trip.get(trip.id, [])
                ],
            }
        )
    return {
        "date": plan.date,
        "waste_carrier": plan.waste_carrier,
        "created_at": plan.created_at,
        "parameters": plan.parameters,
        "summary": plan.summary,
        "unserved": plan.unserved,
        "excluded_trucks": plan.excluded_trucks,
        "trucks": [
            {
                "truck_id": t.truck_id,
                "name": t.name,
                "max_volume_m3": float(t.max_volume_m3),
                "landfill": {
                    "id": t.landfill_id,
                    "name": t.landfill_name,
                    "latitude": t.landfill_latitude,
                    "longitude": t.landfill_longitude,
                },
                "trips": trips_by_truck.get(t.id, []),
            }
            for t in trucks
        ],
    }


def list_available(session: Session) -> list[dict]:
    rows = session.execute(
        select(RoutePlan.date, RoutePlan.waste_carrier).order_by(
            RoutePlan.date.desc(), RoutePlan.waste_carrier
        )
    ).all()
    return [{"date": date_, "waste_carrier": carrier} for date_, carrier in rows]
