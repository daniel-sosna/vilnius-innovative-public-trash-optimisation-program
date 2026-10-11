"""Short-lived, read-only tracking access to routes calculated for the planning screen."""
from collections import OrderedDict
from threading import Lock
from time import monotonic

from app.interfaces.demo.schemas import DemoRoute, DrivingRouteResponse, NavigationResponse
from app.services.demo_prediction import DemoError

_runs = OrderedDict()
_lock = Lock()
RUN_TTL_SECONDS = 3600
MAX_RUNS = 3


def remember_routes(result: NavigationResponse) -> None:
    with _lock:
        now = monotonic()
        for key, entry in list(_runs.items()):
            if entry[0] <= now:
                del _runs[key]
        _runs[result.run_id] = (now + RUN_TTL_SECONDS, {route.truck_id: route for route in result.routes}, result.forecast_date)
        while len(_runs) > MAX_RUNS:
            _runs.popitem(last=False)


def driving_route(run_id: str, truck_id: int) -> DrivingRouteResponse:
    with _lock:
        entry = _runs.get(run_id)
        if entry is None or entry[0] <= monotonic():
            _runs.pop(run_id, None)
            raise DemoError("route_expired", "Maršruto duomenų nėra arba jie nebegalioja. Maršrutų puslapyje apskaičiuokite naują planą.", 404)
        route = entry[1].get(truck_id)
        if route is None:
            raise DemoError("truck_route_missing", "Šiai šiukšliavežei pasirinktame plane maršrutas nepriskirtas.", 404)
        stops = [route.stops[index].model_copy(update={"latitude": leg.path[-1].latitude, "longitude": leg.path[-1].longitude}) for leg in route.legs if (index := leg.stop_index) is not None]
        return DrivingRouteResponse(path=route.path, stops=stops, legs=route.legs)


def latest_routes(forecast_date: str) -> dict[int, DemoRoute]:
    """Routes by truck ID of the newest unexpired run for `forecast_date`; empty when there is none."""
    with _lock:
        now = monotonic()
        for expires, routes, run_date in reversed(list(_runs.values())):
            if expires > now and run_date == forecast_date:
                return dict(routes)
    return {}
