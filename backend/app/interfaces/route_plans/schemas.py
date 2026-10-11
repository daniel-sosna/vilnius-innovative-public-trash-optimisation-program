from datetime import date, datetime

from pydantic import BaseModel


class Figures(BaseModel):
    distance_km: float
    trips: int
    trucks_used: int
    overtime_min: float
    stops_served: int


class Summary(BaseModel):
    optimised: Figures
    baseline: Figures
    saved_km: float
    saved_percent: float
    unserved_stops: int
    stops_total: int
    iterations: int
    stopped_by_wall_limit: bool
    solve_seconds: float


class Stop(BaseModel):
    site_id: int
    address: str | None
    latitude: float
    longitude: float
    load_m3: float
    bin_count: int


class Trip(BaseModel):
    load_m3: float
    distance_km: float
    duration_min: float
    stops: list[Stop]


class Landfill(BaseModel):
    id: int
    name: str
    latitude: float
    longitude: float


class Truck(BaseModel):
    truck_id: int
    name: str
    max_volume_m3: float
    landfill: Landfill
    trips: list[Trip]


class UnservedStop(BaseModel):
    site_id: int
    address: str | None
    latitude: float
    longitude: float
    load_m3: float
    reason: str


class RoutePlanResponse(BaseModel):
    date: date
    waste_carrier: str
    created_at: datetime
    parameters: dict
    summary: Summary
    unserved: list[UnservedStop]
    excluded_trucks: int
    trucks: list[Truck]


class AvailablePlan(BaseModel):
    date: date
    waste_carrier: str
