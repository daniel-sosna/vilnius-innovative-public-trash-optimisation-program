from decimal import Decimal

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.infrastructure.models import Landfill, Truck

PAGE_SIZE = 10
TRUCK_FIELDS = (
    Truck.id,
    Truck.name,
    Truck.max_volume_m3,
    Truck.waste_carrier,
    Truck.landfill_id,
    Truck.available,
)


class TruckNotFound(Exception):
    pass


class InvalidLandfill(Exception):
    pass


def validate_landfill(session: Session, landfill_id: int) -> None:
    # Hold a key-share lock until commit, so a valid choice cannot vanish on save.
    existing = session.scalar(
        select(Landfill.id)
        .where(Landfill.id == landfill_id)
        .with_for_update(read=True, key_share=True)
    )
    if existing is None:
        raise InvalidLandfill


def get_stats(session: Session) -> dict:
    total, available_count, average = session.execute(
        select(
            func.count(Truck.id),
            func.count(Truck.id).filter(Truck.available.is_(True)),
            func.avg(Truck.max_volume_m3),
        ).where(Truck.deleted.is_(False))
    ).one()
    return {
        "total": total,
        "available_count": available_count,
        "average_max_volume_m3": float(average) if average is not None else None,
    }


def list_trucks(
    session: Session,
    *,
    page: int,
    name: str | None,
    available: bool | None,
    minimum: Decimal | None,
    maximum: Decimal | None,
    waste_carrier: str | None,
) -> dict:
    conditions = [Truck.deleted.is_(False)]
    if name and (search := name.strip()):
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        conditions.append(Truck.name.ilike(f"%{escaped}%", escape="\\"))
    if available is not None:
        conditions.append(Truck.available.is_(available))
    if minimum is not None:
        conditions.append(Truck.max_volume_m3 >= minimum)
    if maximum is not None:
        conditions.append(Truck.max_volume_m3 <= maximum)
    if waste_carrier and (carrier := waste_carrier.strip()):
        conditions.append(Truck.waste_carrier == carrier)

    total = (
        session.scalar(select(func.count()).select_from(Truck).where(*conditions)) or 0
    )
    offset = (page - 1) * PAGE_SIZE
    # Avoid overflowing a database OFFSET for a very large but valid page number.
    rows = (
        []
        if offset >= total
        else session.execute(
            select(*TRUCK_FIELDS)
            .where(*conditions)
            .order_by(Truck.id)
            .offset(offset)
            .limit(PAGE_SIZE)
        )
        .mappings()
        .all()
    )
    return {
        "items": [dict(row) for row in rows],
        "total": total,
        "page": page,
        "page_size": PAGE_SIZE,
    }


def get_truck(session: Session, truck_id: int) -> dict:
    row = (
        session.execute(
            select(*TRUCK_FIELDS).where(Truck.id == truck_id, Truck.deleted.is_(False))
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise TruckNotFound
    return dict(row)


def create_truck(session: Session, values: dict) -> dict:
    validate_landfill(session, values["landfill_id"])
    truck = Truck(**values, deleted=False)
    session.add(truck)
    session.flush()
    result = {field.key: getattr(truck, field.key) for field in TRUCK_FIELDS}
    session.commit()
    return result


def patch_truck(session: Session, truck_id: int, values: dict) -> dict:
    if not values:
        return get_truck(session, truck_id)
    existing = session.execute(
        select(Truck.landfill_id)
        .where(Truck.id == truck_id, Truck.deleted.is_(False))
        .with_for_update()
    ).one_or_none()
    if existing is None:
        raise TruckNotFound
    if "landfill_id" in values:
        validate_landfill(session, values["landfill_id"])
    elif existing.landfill_id is None:
        raise InvalidLandfill
    row = (
        session.execute(
            update(Truck)
            .where(Truck.id == truck_id, Truck.deleted.is_(False))
            .values(**values)
            .returning(*TRUCK_FIELDS)
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise TruckNotFound
    result = dict(row)
    session.commit()
    return result


def delete_truck(session: Session, truck_id: int) -> None:
    row = session.execute(
        update(Truck)
        .where(Truck.id == truck_id, Truck.deleted.is_(False))
        .values(deleted=True, available=False)
        .returning(Truck.id)
    ).one_or_none()
    if row is None:
        raise TruckNotFound
    session.commit()
