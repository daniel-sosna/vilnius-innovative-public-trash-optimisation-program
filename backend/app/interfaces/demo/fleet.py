"""Explicitly populate the stored demo fleet; unrelated trucks are untouched."""
from sqlalchemy import select

from app.core.config import Settings
from app.infrastructure.database import create_database_engine, create_session_factory
from app.infrastructure.models import Truck


def main() -> None:
    engine = create_database_engine(Settings())
    try:
        with create_session_factory(engine)() as session:
            template = session.scalar(select(Truck).where(Truck.name == "Demo 1", Truck.deleted.is_(False)))
            if template is None:
                raise SystemExit("Create Demo 1 with a landfill and carrier in the fleet screen first.")
            names = {f"Demo {number}" for number in range(1, 151)}
            existing = {truck.name: truck for truck in session.scalars(select(Truck).where(Truck.name.in_(names), Truck.deleted.is_(False)))}
            created = 0
            for number in range(1, 151):
                name = f"Demo {number}"
                if name in existing:
                    existing[name].available = True
                    continue
                session.add(Truck(name=name, max_volume_m3=template.max_volume_m3,
                                  waste_carrier=template.waste_carrier, landfill_id=template.landfill_id,
                                  available=True, deleted=False))
                created += 1
            session.commit()
            print(f"Demo fleet populated: created {created} trucks; Demo 1–150 enabled.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
