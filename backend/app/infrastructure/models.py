from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Double,
    ForeignKey,
    Identity,
    Index,
    Integer,
    MetaData,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention={"pk": "pk_%(table_name)s"})


class Bin(Base):
    __tablename__ = "bins"
    __table_args__ = (
        CheckConstraint("lat BETWEEN -90 AND 90", name="ck_bins_lat_range"),
        CheckConstraint("lon BETWEEN -180 AND 180", name="ck_bins_lon_range"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    lat: Mapped[float] = mapped_column(Double)
    lon: Mapped[float] = mapped_column(Double)
    address: Mapped[str | None] = mapped_column(Text)


class Truck(Base):
    __tablename__ = "trucks"
    __table_args__ = (
        CheckConstraint("max_bins_per_trip > 0", name="ck_trucks_positive_capacity"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(always=True), primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    max_bins_per_trip: Mapped[int] = mapped_column(Integer)
    available: Mapped[bool] = mapped_column(Boolean)


class Route(Base):
    __tablename__ = "routes"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PLANNED', 'IN_PROGRESS', 'COMPLETED')",
            name="ck_routes_status",
        ),
        Index("ix_routes_truck_id", "truck_id"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(always=True), primary_key=True)
    service_date: Mapped[date] = mapped_column(Date)
    truck_id: Mapped[int] = mapped_column(
        ForeignKey("trucks.id", name="fk_routes_truck_id", ondelete="RESTRICT")
    )
    status: Mapped[str] = mapped_column(Text, server_default=text("'PLANNED'"))


class RouteStop(Base):
    __tablename__ = "route_stops"
    __table_args__ = (
        CheckConstraint("stop_order > 0", name="ck_route_stops_positive_order"),
        UniqueConstraint("route_id", "stop_order", name="uq_route_stops_route_order"),
        Index("ix_route_stops_bin_id", "bin_id"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(always=True), primary_key=True)
    route_id: Mapped[int] = mapped_column(
        ForeignKey("routes.id", name="fk_route_stops_route_id", ondelete="RESTRICT")
    )
    bin_id: Mapped[int] = mapped_column(
        ForeignKey("bins.id", name="fk_route_stops_bin_id", ondelete="RESTRICT")
    )
    stop_order: Mapped[int] = mapped_column(Integer)


class ServiceEvent(Base):
    __tablename__ = "service_events"
    __table_args__ = (
        CheckConstraint("duration >= 0", name="ck_service_events_duration"),
        CheckConstraint(
            "fill_level IN ('EMPTY', 'LESS_THAN_HALF', 'MORE_THAN_HALF', 'FULL')",
            name="ck_service_events_fill_level",
        ),
        Index("ix_service_events_bin_history", "bin_id", "service_ts", "id"),
        Index("ix_service_events_route_id", "route_id"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(always=True), primary_key=True)
    bin_id: Mapped[int] = mapped_column(
        ForeignKey("bins.id", name="fk_service_events_bin_id", ondelete="RESTRICT")
    )
    service_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fill_level: Mapped[str] = mapped_column(Text)
    duration: Mapped[int] = mapped_column(Integer)
    route_id: Mapped[int] = mapped_column(
        ForeignKey("routes.id", name="fk_service_events_route_id", ondelete="RESTRICT")
    )
