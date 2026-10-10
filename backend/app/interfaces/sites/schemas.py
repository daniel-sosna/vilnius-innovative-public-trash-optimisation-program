from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

RequiredText = Annotated[
    str, StringConstraints(strict=True, strip_whitespace=True, min_length=1)
]


class BinCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    object_group: RequiredText
    capacity_m3: Annotated[float, Field(strict=True, gt=0, allow_inf_nan=False)]
    waste_carrier: Literal["Kauno švara", "Biomotorai", "Ecoservice", "Ekonovus"]
    inventory_number: RequiredText
    waste_type: Literal["Mixed municipal waste", "Paper/plastic waste", "Glass waste"]


class SiteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    street: RequiredText
    sub_district: RequiredText
    house_number: RequiredText
    postal_code: (
        Annotated[str, StringConstraints(strict=True, strip_whitespace=True)] | None
    ) = None
    latitude: Annotated[float, Field(strict=True, ge=-90, le=90, allow_inf_nan=False)]
    longitude: Annotated[float, Field(strict=True, ge=-180, le=180, allow_inf_nan=False)]
    bins: Annotated[list[BinCreate], Field(min_length=1)]

    @field_validator("postal_code", mode="before")
    @classmethod
    def empty_postal_code(cls, value: object) -> object:
        return None if isinstance(value, str) and not value.strip() else value


class SiteSummary(BaseModel):
    id: int
    address: str
    bin_count: int


class SitePage(BaseModel):
    items: list[SiteSummary]
    total: int
    page: int
    page_size: int


class WasteTypeCount(BaseModel):
    waste_type: str
    count: int


class SiteStats(BaseModel):
    total_sites: int
    total_bins: int
    total_capacity_m3: float | None
    bins_by_waste_type: list[WasteTypeCount]


class SiteDetail(BaseModel):
    id: int
    address: str
    latitude: float | None
    longitude: float | None
    sub_district: str | None
    street: str | None
    house_number: str | None
    postal_code: str | None
    bin_count: int
    object_groups: list[str]
    total_capacity_m3: float | None
    waste_carriers: list[str]


class BinSummary(BaseModel):
    id: int
    inventory_number: str | None
    waste_type: str
    capacity_m3: float | None


class BinPage(BaseModel):
    items: list[BinSummary]
    total: int
    page: int
    page_size: int
