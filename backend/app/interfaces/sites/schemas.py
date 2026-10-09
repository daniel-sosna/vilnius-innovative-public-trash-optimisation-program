from pydantic import BaseModel


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
