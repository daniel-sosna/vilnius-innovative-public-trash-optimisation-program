from datetime import datetime

from pydantic import BaseModel


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
