from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.infrastructure.models import Bin, Site


class SiteNotFoundError(Exception):
    pass


def list_bins(session: Session, site_id: int, *, page: int, page_size: int) -> dict:
    if (
        site_id > 2**63 - 1
        or session.scalar(select(Site.id).where(Site.id == site_id)) is None
    ):
        raise SiteNotFoundError
    total = session.scalar(
        select(func.count()).select_from(Bin).where(Bin.site_id == site_id)
    )
    offset = (page - 1) * page_size
    rows = (
        []
        if offset >= total
        else session.execute(
            select(Bin.id, Bin.inventory_number, Bin.waste_type, Bin.capacity_m3)
            .where(Bin.site_id == site_id)
            .order_by(Bin.id)
            .offset(offset)
            .limit(page_size)
        )
        .mappings()
        .all()
    )
    return {
        "items": [
            {
                **dict(row),
                "capacity_m3": float(row["capacity_m3"])
                if row["capacity_m3"] is not None
                else None,
            }
            for row in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def list_sites(
    session: Session, *, page: int, page_size: int, address: str | None
) -> dict:
    conditions = []
    if address and (search := address.strip()):
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        conditions.append(Site.address.ilike(f"%{escaped}%", escape="\\"))

    total = session.scalar(select(func.count()).select_from(Site).where(*conditions))
    offset = (page - 1) * page_size
    # Do not send an arbitrarily large Python integer to PostgreSQL OFFSET.
    rows = (
        []
        if offset >= total
        else session.execute(
            select(Site.id, Site.address)
            .where(*conditions)
            .order_by(Site.id)
            .offset(offset)
            .limit(page_size)
        ).all()
    )
    counts = (
        dict(
            session.execute(
                select(Bin.site_id, func.count(Bin.id))
                .where(Bin.site_id.in_([row.id for row in rows]))
                .group_by(Bin.site_id)
            ).all()
        )
        if rows
        else {}
    )
    return {
        "items": [
            {"id": row.id, "address": row.address, "bin_count": counts.get(row.id, 0)}
            for row in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def get_stats(session: Session) -> dict:
    total_sites = session.scalar(select(func.count()).select_from(Site))
    total_bins, capacity = session.execute(
        select(func.count(Bin.id), func.sum(Bin.capacity_m3))
    ).one()
    groups = (
        session.execute(
            select(Bin.waste_type, func.count(Bin.id).label("count"))
            .group_by(Bin.waste_type)
            .order_by(Bin.waste_type)
        )
        .mappings()
        .all()
    )
    return {
        "total_sites": total_sites,
        "total_bins": total_bins,
        # SUM stays NUMERIC in SQL; convert only at the JSON response boundary.
        "total_capacity_m3": float(capacity) if capacity is not None else None,
        "bins_by_waste_type": [dict(group) for group in groups],
    }


def get_site(session: Session, site_id: int) -> dict:
    # BIGINT identities cannot contain a larger positive integer.
    if site_id > 2**63 - 1:
        raise SiteNotFoundError
    site = (
        session.execute(
            select(Site.id, Site.address, Site.latitude, Site.longitude).where(
                Site.id == site_id
            )
        )
        .mappings()
        .one_or_none()
    )
    if site is None:
        raise SiteNotFoundError

    fields = (Bin.sub_district, Bin.street, Bin.house_number, Bin.postal_code)
    first_bin = (
        session.execute(
            select(*fields).where(Bin.site_id == site_id).order_by(Bin.id).limit(1)
        )
        .mappings()
        .one_or_none()
    )
    count, capacity = session.execute(
        select(func.count(Bin.id), func.sum(Bin.capacity_m3)).where(
            Bin.site_id == site_id
        )
    ).one()

    def distinct_values(column) -> list[str]:
        return list(
            session.scalars(
                select(column)
                .where(Bin.site_id == site_id, column.is_not(None))
                .distinct()
                .order_by(column)
            )
        )

    return {
        **dict(site),
        **{
            field.key: first_bin[field.key] if first_bin is not None else None
            for field in fields
        },
        "bin_count": count,
        "total_capacity_m3": float(capacity) if capacity is not None else None,
        "object_groups": distinct_values(Bin.object_group),
        "waste_carriers": distinct_values(Bin.waste_carrier),
    }
