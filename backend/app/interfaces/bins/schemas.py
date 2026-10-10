from datetime import datetime

from pydantic import BaseModel


class LatestBinService(BaseModel):
    date: datetime
    was_serviced: bool


class PublicBin(BaseModel):
    id: int
    address: str
    inventory_number: str | None
    waste_type: str
    latitude: float
    longitude: float
    latest_service: LatestBinService | None


class ResidentRequestSuccess(BaseModel):
    success: bool


class HistoryEntry(BaseModel):
    id: int
    date: datetime
    was_serviced: bool
    non_serviced_reason: str | None
    fill_level: int | None


class HistoryPage(BaseModel):
    items: list[HistoryEntry]
    total: int
    page: int
    page_size: int
    successful_service_percentage: float | None
    unsuccessful_service_percentage: float | None
