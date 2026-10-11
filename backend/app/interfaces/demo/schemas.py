from datetime import date
from uuid import uuid4
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator, model_validator


def calendar_day(value: str, start: str, end: str) -> str:
    if not isinstance(value, str) or len(value) != 10:
        raise ValueError("Use a YYYY-MM-DD calendar date")
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise ValueError("Use a valid calendar date") from None
    if parsed.isoformat() != value or not start <= value <= end:
        raise ValueError(f"Date must be between {start} and {end}")
    return value


class PredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    project_date: str

    @field_validator("project_date")
    @classmethod
    def september(cls, value: str) -> str:
        return calendar_day(value, "2026-09-01", "2026-09-30")


class PredictedBin(BaseModel):
    bin_id: int
    site_id: int
    fill_level: Literal[3, 4]
    latitude: float | None
    longitude: float | None
    address: str
    waste_carrier: str | None


class PredictionResponse(BaseModel):
    project_date: str
    forecast_date: str
    evaluated_count: int
    due_count: int
    unmappable_count: int
    bins: list[PredictedBin]


class NavigationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    forecast_date: str
    bin_ids: list[Annotated[StrictInt, Field(gt=0)]] = Field(min_length=1, max_length=100000)
    fill_levels: dict[int, Literal[3, 4]]

    @model_validator(mode="after")
    def prediction_coverage(self):
        if set(self.fill_levels) != set(self.bin_ids):
            raise ValueError("Fill levels must cover exactly the selected bin IDs")
        return self

    @field_validator("forecast_date")
    @classmethod
    def forecast_range(cls, value: str) -> str:
        return calendar_day(value, "2026-09-02", "2026-10-01")

    @field_validator("bin_ids")
    @classmethod
    def unique(cls, value: list[int]) -> list[int]:
        if len(set(value)) != len(value):
            raise ValueError("Bin IDs must be unique")
        return value


class Coordinate(BaseModel):
    latitude: float
    longitude: float


class Stop(Coordinate):
    site_id: int
    bin_ids: list[int]


class DrivingLeg(BaseModel):
    path: list[Coordinate]
    distance_m: float
    stop_index: int | None = None


class DemoRoute(BaseModel):
    truck_id: int
    truck_name: str
    route_id: str
    path: list[Coordinate]
    stops: list[Stop]
    legs: list[DrivingLeg]


class UnservedStop(Stop):
    reason: str


class NavigationResponse(BaseModel):
    run_id: str = Field(default_factory=lambda: uuid4().hex)
    forecast_date: str
    source: Literal["pyvrp-osrm"] = "pyvrp-osrm"
    routes: list[DemoRoute]
    unserved: list[UnservedStop] = Field(default_factory=list)


class DrivingRouteResponse(BaseModel):
    source: Literal["osrm"] = "osrm"
    path: list[Coordinate]
    stops: list[Coordinate]
    legs: list[DrivingLeg]
