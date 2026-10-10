from decimal import Decimal
from math import isfinite
from typing import Annotated

from pydantic import (
    BaseModel,
    BeforeValidator,
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
WasteCarrier = Annotated[
    str, StringConstraints(strict=True, strip_whitespace=True, min_length=1)
]


def numeric_volume(value: object) -> Decimal:
    # JSON booleans and numeric strings must not be coerced to a capacity.
    if type(value) not in (int, float):
        raise ValueError("Volume must be a JSON number")
    try:
        finite = isfinite(value)
    except OverflowError:
        finite = False
    if not finite:
        raise ValueError("Volume must be finite")
    return Decimal(str(value))


TruckVolume = Annotated[
    Decimal,
    BeforeValidator(numeric_volume, json_schema_input_type=int | float),
    Field(gt=0, allow_inf_nan=False),
]
LandfillId = Annotated[StrictInt, Field(gt=0, le=2147483647)]


class TruckCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: TruckName
    max_volume_m3: TruckVolume
    waste_carrier: WasteCarrier
    landfill_id: LandfillId
    available: StrictBool


class TruckPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: TruckName | None = None
    max_volume_m3: TruckVolume | None = None
    waste_carrier: WasteCarrier | None = None
    landfill_id: LandfillId | None = None
    available: StrictBool | None = None

    @field_validator(
        "name",
        "max_volume_m3",
        "waste_carrier",
        "landfill_id",
        "available",
        mode="before",
    )
    @classmethod
    def reject_explicit_null(cls, value: object) -> object:
        if value is None:
            raise ValueError("Field cannot be null")
        return value


class TruckResponse(BaseModel):
    id: int
    name: str
    max_volume_m3: float
    waste_carrier: str
    landfill_id: int | None
    available: bool


class TruckPage(BaseModel):
    items: list[TruckResponse]
    total: int
    page: int
    page_size: int


class TruckStats(BaseModel):
    total: int
    available_count: int
    average_max_volume_m3: float | None
