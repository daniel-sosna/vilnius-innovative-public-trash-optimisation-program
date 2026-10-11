from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RouteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    truck_id: Annotated[int, Field(ge=1, le=2**31 - 1)]


class PathPoint(BaseModel):
    latitude: float
    longitude: float


class RouteBin(BaseModel):
    bin_id: int
    inventory_number: str | None
    waste_type: str


class RouteStop(BaseModel):
    site_id: int
    address: str | None
    path_index: int
    bins: list[RouteBin]


class RouteResponse(BaseModel):
    truck_id: int
    plan_date: date
    path: list[PathPoint]
    stops: list[RouteStop]


class ServiceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    bin_id: Annotated[int, Field(ge=1, le=2**63 - 1)]
    fill_level: Annotated[int, Field(strict=True, ge=0, le=4)]


class ServiceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    services: Annotated[list[ServiceItem], Field(min_length=1, max_length=200)]

    @field_validator("services")
    @classmethod
    def unique_bins(cls, value: list[ServiceItem]) -> list[ServiceItem]:
        if len({item.bin_id for item in value}) != len(value):
            raise ValueError("Bin IDs must be unique")
        return value


class ServiceRecord(BaseModel):
    id: int
    bin_id: int
    date: datetime
    fill_level: int


class ServiceResponse(BaseModel):
    records: list[ServiceRecord]
