from typing import Literal

from pydantic import BaseModel


class LandfillProperties(BaseModel):
    name: str
    operator: str | None
    address: str | None
    coordinate_quality: str | None


class PointGeometry(BaseModel):
    type: Literal["Point"] = "Point"
    coordinates: tuple[float, float]


class LandfillFeature(BaseModel):
    type: Literal["Feature"] = "Feature"
    id: int
    geometry: PointGeometry
    properties: LandfillProperties


class LandfillFeatureCollection(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[LandfillFeature]


class PolygonGeometry(BaseModel):
    type: Literal["Polygon"] = "Polygon"
    coordinates: list[list[tuple[float, float]]]


class PopulationProperties(BaseModel):
    density_per_ha: int | None
    suppressed: bool
    area_ha: float
    residents: float | None


class PopulationFeature(BaseModel):
    type: Literal["Feature"] = "Feature"
    id: int
    geometry: PolygonGeometry
    properties: PopulationProperties


class PopulationFeatureCollection(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[PopulationFeature]


class BinProperties(BaseModel):
    inventory_number: str | None
    waste_type: str
    capacity_m3: float | None


class BinFeature(BaseModel):
    type: Literal["Feature"] = "Feature"
    id: int
    geometry: PointGeometry
    properties: BinProperties


class BinFeatureCollection(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[BinFeature]
