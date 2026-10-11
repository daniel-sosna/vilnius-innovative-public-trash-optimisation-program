import math
import random
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.infrastructure.models import Landfill, Truck
from app.services.collection_plan import get_plan

DEMO_PREFIX = "DEMO "

# ASSUMPTIONS: invented demo fleet, not real fleet data.
DEFAULT_CAPACITIES = (10, 16, 20)
DEFAULT_SHIFT_MINUTES = 480
# Rough length of one trip (drive, service, unload) used only to size the fleet.
DEFAULT_TRIP_MINUTES = 90
SLACK = 1.2


class NoCollectionPlan(Exception):
    pass


class NoLandfills(Exception):
    pass


@dataclass
class CarrierFleet:
    carrier: str
    stops: int
    load_m3: float
    trucks: int


def plan_fleet(
    session: Session,
    day: date,
    capacities: tuple[int, ...] = DEFAULT_CAPACITIES,
    shift_minutes: int = DEFAULT_SHIFT_MINUTES,
    trip_minutes: int = DEFAULT_TRIP_MINUTES,
    seed: int = 0,
) -> list[CarrierFleet]:
    """Replace the demo trucks with a fleet sized from the stored collection plan of `day`.

    Per carrier: trucks = ceil(SLACK * load / (mean capacity * trips per shift)). Trucks
    named with DEMO_PREFIX are replaced; every other truck is left alone. Commits once.
    """
    plan = get_plan(session, day)
    carriers = {c: stops for c, stops in plan.items() if c is not None and stops}
    if not carriers:
        raise NoCollectionPlan
    landfills = list(session.scalars(select(Landfill.id).order_by(Landfill.id)))
    if not landfills:
        raise NoLandfills
    rng = random.Random(seed)
    mean_capacity = sum(capacities) / len(capacities)
    trips_per_shift = shift_minutes / trip_minutes
    session.execute(delete(Truck).where(Truck.name.startswith(DEMO_PREFIX)))
    fleets = []
    next_landfill = 0
    for carrier in sorted(carriers):
        stops = carriers[carrier]
        load = float(sum(s["overall_predicted_fill_m3"] for s in stops))
        count = max(1, math.ceil(SLACK * load / (mean_capacity * trips_per_shift)))
        for number in range(1, count + 1):
            session.add(
                Truck(
                    name=f"{DEMO_PREFIX}{carrier} {number}",
                    max_volume_m3=Decimal(rng.choice(capacities)),
                    waste_carrier=carrier,
                    landfill_id=landfills[next_landfill % len(landfills)],
                    available=True,
                )
            )
            next_landfill += 1
        fleets.append(CarrierFleet(carrier, len(stops), load, count))
    session.commit()
    return fleets
