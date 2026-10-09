from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    ARRAY,
    BigInteger,
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
    Numeric,
    SmallInteger,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention={"pk": "pk_%(table_name)s"})


class Site(Base):
    __tablename__ = "sites"
    __table_args__ = (
        UniqueConstraint("site_key", name="uq_sites_site_key"),
        CheckConstraint("latitude BETWEEN -90 AND 90", name="ck_sites_latitude_range"),
        CheckConstraint(
            "longitude BETWEEN -180 AND 180", name="ck_sites_longitude_range"
        ),
    )
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    site_key: Mapped[str] = mapped_column(Text)
    address: Mapped[str] = mapped_column(Text)
    latitude: Mapped[float] = mapped_column(Double)
    longitude: Mapped[float] = mapped_column(Double)
    bins: Mapped[list["Bin"]] = relationship(
        back_populates="site", passive_deletes="all"
    )


class Bin(Base):
    __tablename__ = "bins"
    __table_args__ = (
        UniqueConstraint("external_id", name="uq_bins_external_id"),
        CheckConstraint("latitude BETWEEN -90 AND 90", name="ck_bins_latitude_range"),
        CheckConstraint(
            "longitude BETWEEN -180 AND 180", name="ck_bins_longitude_range"
        ),
        CheckConstraint("client_count >= 0", name="ck_bins_client_count"),
        Index("ix_bins_site_id", "site_id"),
    )
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    site_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("sites.id", name="fk_bins_site_id", ondelete="RESTRICT")
    )
    external_id: Mapped[int] = mapped_column(BigInteger)
    inventory_number: Mapped[str | None] = mapped_column(Text)
    waste_type: Mapped[str] = mapped_column(Text)
    capacity_m3: Mapped[Decimal | None] = mapped_column(Numeric)
    latitude: Mapped[float] = mapped_column(Double)
    longitude: Mapped[float] = mapped_column(Double)
    district: Mapped[str | None] = mapped_column(Text)
    region: Mapped[str | None] = mapped_column(Text)
    sub_district: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(Text)
    street: Mapped[str | None] = mapped_column(Text)
    house_number: Mapped[str | None] = mapped_column(Text)
    postal_code: Mapped[str | None] = mapped_column(Text)
    territory_type: Mapped[str | None] = mapped_column(Text)
    object_group: Mapped[str | None] = mapped_column(Text)
    waste_carrier: Mapped[str | None] = mapped_column(Text)
    client_count: Mapped[int | None] = mapped_column(Integer)
    site: Mapped[Site] = relationship(back_populates="bins")
    history: Mapped[list["BinHist"]] = relationship(
        back_populates="bin", cascade="all, delete-orphan", passive_deletes=True
    )
    resident_requests: Mapped[list["ResidentRequest"]] = relationship(
        back_populates="bin", cascade="all, delete-orphan", passive_deletes=True
    )


class ResidentRequest(Base):
    __tablename__ = "resident_requests"
    __table_args__ = (Index("ix_resident_requests_bin_id", "bin_id"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    bin_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("bins.id", name="fk_resident_requests_bin_id", ondelete="CASCADE"),
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=text("(statement_timestamp() AT TIME ZONE 'Europe/Vilnius')"),
    )
    bin: Mapped[Bin] = relationship(back_populates="resident_requests")


class BinHist(Base):
    __tablename__ = "bin_hist"
    __table_args__ = (
        UniqueConstraint("bin_id", "date", "was_serviced", name="uq_bin_hist_event"),
        CheckConstraint("fill_level BETWEEN 0 AND 3", name="ck_bin_hist_fill_level"),
    )
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    bin_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("bins.id", name="fk_bin_hist_bin_id", ondelete="CASCADE")
    )
    date: Mapped[datetime] = mapped_column(DateTime(timezone=False))
    was_serviced: Mapped[bool] = mapped_column(Boolean)
    non_serviced_reason: Mapped[str | None] = mapped_column(Text)
    fill_level: Mapped[int | None] = mapped_column(SmallInteger)
    bin: Mapped[Bin] = relationship(back_populates="history")


class VasaImportRun(Base):
    __tablename__ = "vasa_import_runs"
    __table_args__ = (
        CheckConstraint(
            "phase IN ('tiles', 'history', 'finalize', 'complete')",
            name="ck_vasa_import_runs_phase",
        ),
        Index("ix_vasa_import_runs_scope", "scope_key", "id"),
    )
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    scope_key: Mapped[str] = mapped_column(Text)
    coverage: Mapped[dict] = mapped_column(JSONB)
    phase: Mapped[str] = mapped_column(Text)
    diagnostics: Mapped[int] = mapped_column(Integer, server_default=text("0"))


class VasaImportProgress(Base):
    __tablename__ = "vasa_import_progress"
    __table_args__ = (
        UniqueConstraint(
            "run_id", "kind", "work_key", name="uq_vasa_import_progress_work"
        ),
    )
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    run_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "vasa_import_runs.id",
            name="fk_vasa_import_progress_run_id",
            ondelete="CASCADE",
        ),
    )
    kind: Mapped[str] = mapped_column(Text)
    work_key: Mapped[str] = mapped_column(Text)
    complete: Mapped[bool] = mapped_column(Boolean)
    details: Mapped[dict] = mapped_column(JSONB)


class Landfill(Base):
    __tablename__ = "landfills"
    __table_args__ = (
        UniqueConstraint("source_id", name="uq_landfills_source_id"),
        CheckConstraint(
            "latitude BETWEEN -90 AND 90", name="ck_landfills_latitude_range"
        ),
        CheckConstraint(
            "longitude BETWEEN -180 AND 180", name="ck_landfills_longitude_range"
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer, Identity(always=True, start=1), primary_key=True
    )
    source_id: Mapped[str | None] = mapped_column(Text)
    dataset_name: Mapped[str | None] = mapped_column(Text)
    dataset_description: Mapped[str | None] = mapped_column(Text)
    latitude: Mapped[float | None] = mapped_column(Double)
    longitude: Mapped[float | None] = mapped_column(Double)
    name: Mapped[str] = mapped_column(Text)
    operator: Mapped[str | None] = mapped_column(Text)
    address: Mapped[str | None] = mapped_column(Text)
    facility_role: Mapped[str | None] = mapped_column(Text)
    waste_streams: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    status: Mapped[str | None] = mapped_column(Text)
    coordinate_quality: Mapped[str | None] = mapped_column(Text)
    coordinate_source: Mapped[str | None] = mapped_column(Text)
    facility_source: Mapped[str | None] = mapped_column(Text)
    municipal_arrangement_source: Mapped[str | None] = mapped_column(Text)
    current_status_source: Mapped[str | None] = mapped_column(Text)
    verified_at: Mapped[date | None] = mapped_column(Date)


class Truck(Base):
    __tablename__ = "trucks"
    __table_args__ = (
        CheckConstraint(
            "max_volume_m3 > 0 AND max_volume_m3 NOT IN "
            "('NaN'::numeric, 'Infinity'::numeric, '-Infinity'::numeric)",
            name="ck_trucks_positive_finite_volume",
        ),
        CheckConstraint(
            r"btrim(name, U&'\0009\000a\000b\000c\000d\001c\001d\001e\001f\0020\0085\00a0\1680\2000\2001\2002\2003\2004\2005\2006\2007\2008\2009\200a\2028\2029\202f\205f\3000') <> ''",
            name="ck_trucks_nonblank_name",
        ),
        CheckConstraint(
            "NOT deleted OR NOT available", name="ck_trucks_deleted_unavailable"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(always=True), primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    max_volume_m3: Mapped[Decimal] = mapped_column(Numeric)
    waste_carrier: Mapped[str] = mapped_column(Text)
    landfill_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("landfills.id", name="fk_trucks_landfill_id", ondelete="RESTRICT"),
    )
    available: Mapped[bool] = mapped_column(Boolean)
    deleted: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
