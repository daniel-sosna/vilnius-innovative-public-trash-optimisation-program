from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    StringConstraints,
    field_validator,
)

TruckName = Annotated[
    str, StringConstraints(strict=True, strip_whitespace=True, min_length=1)
]
SiteCapacity = Annotated[StrictInt, Field(ge=1, le=99)]


class TruckCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: TruckName
    max_bins_per_trip: SiteCapacity
    available: StrictBool


class TruckPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: TruckName | None = None
    max_bins_per_trip: SiteCapacity | None = None
    available: StrictBool | None = None

    @field_validator("name", "max_bins_per_trip", "available", mode="before")
    @classmethod
    def reject_explicit_null(cls, value: object) -> object:
        if value is None:
            raise ValueError("Field cannot be null")
        return value


class TruckResponse(BaseModel):
    id: int
    name: str
    max_bins_per_trip: int
    available: bool
    deleted: bool


class TruckPage(BaseModel):
    items: list[TruckResponse]
    total: int
    page: int
    page_size: int


class TruckStats(BaseModel):
    total: int
    available_count: int
    average_max_bins_per_trip: float | None
