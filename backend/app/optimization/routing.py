"""Multi-trip route planning of one carrier's trucks, and its nearest-neighbour baseline.

Pure functions on plain inputs. Distances are straight-line (haversine) times a detour
factor, so every distance and duration here is an estimate. Distances are whole metres,
durations whole seconds, loads whole litres (rounded up for stops, down for capacities).
"""

import math
import time
from dataclasses import asdict, dataclass

import numpy as np

EARTH_RADIUS_M = 6_371_000
# Cap for overtime in the solver; overtime is limited by its price, not by this.
MAX_OVERTIME_S = 12 * 3600


@dataclass(frozen=True)
class Params:
    # ASSUMPTIONS: urban driving speed, road/straight-line ratio, handling times, shift.
    speed_kmh: float = 30.0
    detour_factor: float = 1.3
    service_min: float = 5.0
    unload_min: float = 15.0
    shift_min: float = 480.0
    # Cost of one overtime minute, in km of driving.
    overtime_penalty: float = 10.0
    max_iterations: int = 1000
    seed: int = 0
    # Safety valve only; reaching it makes the result depend on the machine.
    wall_limit_s: int = 900


@dataclass(frozen=True)
class Point:
    latitude: float
    longitude: float


@dataclass(frozen=True)
class StopIn:
    point: Point
    load_m3: float


@dataclass(frozen=True)
class TruckIn:
    capacity_m3: float
    depot: int  # index into the depots list


@dataclass
class Trip:
    stops: list[int]  # indices into the stops list, in visiting order
    load_m3: float
    distance_m: int
    duration_s: int


@dataclass
class Figures:
    distance_km: float
    trips: int
    trucks_used: int
    overtime_min: float
    stops_served: int


@dataclass
class Plan:
    trips: dict[int, list[Trip]]  # truck index -> trips (trucks without trips are absent)
    figures: Figures


@dataclass
class Result:
    optimised: Plan
    baseline: Plan
    unserved: list[tuple[int, str]]  # (stop index, reason)
    saved_km: float
    saved_percent: float
    iterations: int
    stopped_by_wall_limit: bool
    solve_seconds: float


def _litres_up(m3: float) -> int:
    return math.ceil(round(m3 * 1000, 6))


def _litres_down(m3: float) -> int:
    return math.floor(round(m3 * 1000, 6))


def build_matrices(depots: list[Point], stops: list[StopIn], params: Params):
    """Distance (m) and duration (s) matrices over depots first, then stops.

    Arriving at a depot includes the unloading time. Service time at a stop is not in the
    matrix. The diagonal is zero.
    """
    points = list(depots) + [s.point for s in stops]
    lat = np.radians([p.latitude for p in points])
    lon = np.radians([p.longitude for p in points])
    dlat = lat[:, None] - lat[None, :]
    dlon = lon[:, None] - lon[None, :]
    a = np.sin(dlat / 2) ** 2 + np.cos(lat)[:, None] * np.cos(lat)[None, :] * np.sin(dlon / 2) ** 2
    dist = np.rint(2 * EARTH_RADIUS_M * np.arcsin(np.sqrt(a)) * params.detour_factor).astype(np.int64)
    dur = np.rint(dist / (params.speed_kmh / 3.6)).astype(np.int64)
    dur[:, : len(depots)] += int(round(params.unload_min * 60))
    np.fill_diagonal(dur, 0)
    return dist, dur


def _make_trip(stops: list[int], depot: int, num_depots: int, loads_l: list[int], dist, dur, service_s: int) -> Trip:
    nodes = [depot] + [num_depots + s for s in stops] + [depot]
    distance = sum(int(dist[a, b]) for a, b in zip(nodes, nodes[1:]))
    duration = sum(int(dur[a, b]) for a, b in zip(nodes, nodes[1:])) + service_s * len(stops)
    return Trip(stops, sum(loads_l[s] for s in stops) / 1000, distance, duration)


def _figures(trips: dict[int, list[Trip]], shift_s: int) -> Figures:
    used = {t: ts for t, ts in trips.items() if ts}
    overtime = sum(max(0, sum(trip.duration_s for trip in ts) - shift_s) for ts in used.values())
    return Figures(
        distance_km=sum(trip.distance_m for ts in used.values() for trip in ts) / 1000,
        trips=sum(len(ts) for ts in used.values()),
        trucks_used=len(used),
        overtime_min=overtime / 60,
        stops_served=sum(len(trip.stops) for ts in used.values() for trip in ts),
    )


def _optimise(depots, stops, trucks, loads_l, dist, dur, params: Params):
    """Solve with PyVRP; returns (trips per truck, iterations, hit the wall limit, seconds)."""
    from pyvrp import Client, Depot, Location, ProblemData, VehicleType, solve
    from pyvrp.stop import MaxIterations, MaxRuntime, MultipleCriteria

    num_depots = len(depots)
    service_s = int(round(params.service_min * 60))
    shift_s = int(round(params.shift_min * 60))
    # Overtime second in cost units: 1 km costs 1000 (distance in metres).
    overtime_cost = max(1, round(params.overtime_penalty * 1000 / 60))
    locations = [Location(p.longitude, p.latitude) for p in depots] + [
        Location(s.point.longitude, s.point.latitude) for s in stops
    ]
    clients = [
        Client(num_depots + i, delivery=[loads_l[i]], service_duration=service_s)
        for i in range(len(stops))
    ]
    vehicle_types = [
        VehicleType(
            1,
            capacity=[_litres_down(t.capacity_m3)],
            start_depot=t.depot,
            end_depot=t.depot,
            reload_depots=[t.depot],
            shift_duration=shift_s,
            max_overtime=MAX_OVERTIME_S,
            unit_overtime_cost=overtime_cost,
        )
        for t in trucks
    ]
    data = ProblemData(
        locations, clients, [Depot(i) for i in range(num_depots)], vehicle_types, [dist], [dur]
    )
    started = time.monotonic()
    result = solve(
        data,
        MultipleCriteria([MaxIterations(params.max_iterations), MaxRuntime(params.wall_limit_s)]),
        seed=params.seed,
        display=False,
    )
    seconds = time.monotonic() - started
    solution = result.best
    if not solution.is_feasible():
        raise RuntimeError("the solver found no feasible plan")
    trips: dict[int, list[Trip]] = {}
    for route in solution.routes():
        truck = route.vehicle_type()
        by_trip: dict[int, list[int]] = {}
        for activity in route.schedule():
            if activity.is_client():
                by_trip.setdefault(activity.trip, []).append(activity.idx)
        trips[truck] = [
            _make_trip(by_trip[k], trucks[truck].depot, num_depots, loads_l, dist, dur, service_s)
            for k in sorted(by_trip)
        ]
    return trips, result.num_iterations, result.num_iterations < params.max_iterations, seconds


def _baseline(trucks, loads_l, dist, dur, num_depots, service_s: int) -> dict[int, list[Trip]]:
    """Nearest neighbour: trucks take turns; a turn is one trip.

    On a turn the truck drives from its landfill to the nearest unserved stop that still
    fits, repeatedly, and returns to unload when none fits.
    """
    n = len(loads_l)
    loads = np.array(loads_l, dtype=np.int64)
    capacities = [_litres_down(t.capacity_m3) for t in trucks]
    unserved = np.ones(n, dtype=bool)
    trips: dict[int, list[Trip]] = {}
    turn = 0
    stalled = 0
    while unserved.any() and stalled < len(trucks):
        truck = turn % len(trucks)
        turn += 1
        position = trucks[truck].depot
        remaining = capacities[truck]
        visited: list[int] = []
        while True:
            fits = unserved & (loads <= remaining)
            if not fits.any():
                break
            candidates = np.flatnonzero(fits)
            nearest = int(candidates[np.argmin(dist[position, num_depots + candidates])])
            visited.append(nearest)
            unserved[nearest] = False
            remaining -= int(loads[nearest])
            position = num_depots + nearest
        if visited:
            stalled = 0
            trips.setdefault(truck, []).append(
                _make_trip(visited, trucks[truck].depot, num_depots, loads_l, dist, dur, service_s)
            )
        else:
            stalled += 1
    return trips


def plan_routes(depots: list[Point], stops: list[StopIn], trucks: list[TruckIn], params: Params) -> Result:
    """Plan multi-trip routes for `trucks` over `stops` and compare them with the baseline.

    A stop whose load exceeds every truck is left out and reported as unserved.
    """
    if not trucks:
        raise ValueError("no trucks to plan with")
    largest = max(_litres_down(t.capacity_m3) for t in trucks)
    loads_all = [_litres_up(s.load_m3) for s in stops]
    keep = [i for i, load in enumerate(loads_all) if load <= largest]
    unserved = [
        (i, f"load {stops[i].load_m3:.2f} m3 exceeds the capacity of every truck ({largest / 1000:.2f} m3)")
        for i, load in enumerate(loads_all)
        if load > largest
    ]
    kept = [stops[i] for i in keep]
    loads_l = [loads_all[i] for i in keep]
    if not kept:
        empty = Plan({}, _figures({}, 0))
        return Result(empty, empty, unserved, 0.0, 0.0, 0, False, 0.0)
    dist, dur = build_matrices(depots, kept, params)
    shift_s = int(round(params.shift_min * 60))
    service_s = int(round(params.service_min * 60))
    trips, iterations, wall, seconds = _optimise(depots, kept, trucks, loads_l, dist, dur, params)
    baseline = _baseline(trucks, loads_l, dist, dur, len(depots), service_s)

    def remap(plan: dict[int, list[Trip]]) -> dict[int, list[Trip]]:
        for ts in plan.values():
            for trip in ts:
                trip.stops = [keep[s] for s in trip.stops]
        return plan

    optimised = Plan(trips, _figures(trips, shift_s))
    reference = Plan(baseline, _figures(baseline, shift_s))
    remap(optimised.trips)
    remap(reference.trips)
    saved = reference.figures.distance_km - optimised.figures.distance_km
    percent = 100 * saved / reference.figures.distance_km if reference.figures.distance_km else 0.0
    return Result(optimised, reference, unserved, saved, percent, iterations, wall, seconds)


def params_dict(params: Params) -> dict:
    return asdict(params)
