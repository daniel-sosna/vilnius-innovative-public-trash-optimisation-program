from datetime import date

from pydantic import BaseModel


class LandfillResponse(BaseModel):
    id: int
    source_id: str | None
    dataset_name: str | None
    dataset_description: str | None
    latitude: float | None
    longitude: float | None
    name: str
    operator: str | None
    address: str | None
    facility_role: str | None
    waste_streams: list[str] | None
    status: str | None
    coordinate_quality: str | None
    coordinate_source: str | None
    facility_source: str | None
    municipal_arrangement_source: str | None
    current_status_source: str | None
    verified_at: date | None
