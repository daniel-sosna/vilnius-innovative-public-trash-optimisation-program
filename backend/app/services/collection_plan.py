from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.infrastructure.database import SYNC_LOCK_TIMEOUT_MS
from app.ml.fill_prediction import predict_fill_levels

# ASSUMPTION: share of a bin's capacity that each predicted fill level stands for
# (above 1 means over-full). Not measured data; the only place the levels become volumes.
FILL_SHARES = {0: "0.2", 1: "0.5", 2: "0.8", 3: "1.0", 4: "1.5"}
FILL_SHARE_SQL = "CASE f.predicted_fill " + " ".join(
    f"WHEN {level} THEN {share}" for level, share in FILL_SHARES.items()
) + " END"

CREATE_FILL_SQL = text(
    """
    CREATE TEMP TABLE bin_fill (
        bin_id BIGINT PRIMARY KEY,
        predicted_fill SMALLINT NOT NULL,
        due BOOLEAN NOT NULL
    ) ON COMMIT DROP
    """
)

# A stop exists for each (carrier, site) with a due bin. Its totals cover all the
# carrier's bins at the site, because the truck empties all of them.
INSERT_STOPS_SQL = text(
    f"""
    INSERT INTO collection_stops (
        date, waste_carrier, site_id, overall_volume_m3, overall_predicted_fill_m3
    )
    SELECT :day, b.waste_carrier, b.site_id,
           SUM(COALESCE(b.capacity_m3, 0)),
           SUM(COALESCE(b.capacity_m3, 0) * {FILL_SHARE_SQL})
    FROM bin_fill AS f
    JOIN bins AS b ON b.id = f.bin_id
    GROUP BY b.waste_carrier, b.site_id
    HAVING bool_or(f.due)
    """
)

INSERT_STOP_BINS_SQL = text(
    """
    INSERT INTO stop_bins (stop_id, bin_id, predicted_fill, due)
    SELECT s.id, f.bin_id, f.predicted_fill, f.due
    FROM bin_fill AS f
    JOIN bins AS b ON b.id = f.bin_id
    JOIN collection_stops AS s
      ON s.date = :day
     AND s.site_id = b.site_id
     AND s.waste_carrier IS NOT DISTINCT FROM b.waste_carrier
    """
)

STOPS_PER_CARRIER_SQL = text(
    "SELECT waste_carrier, count(*) FROM collection_stops WHERE date = :day "
    "GROUP BY waste_carrier"
)

NO_CAPACITY_SQL = text(
    "SELECT count(*) FROM stop_bins AS sb "
    "JOIN collection_stops AS s ON s.id = sb.stop_id AND s.date = :day "
    "JOIN bins AS b ON b.id = sb.bin_id WHERE b.capacity_m3 IS NULL"
)

READ_SQL = text(
    """
    SELECT s.id AS stop_id, s.waste_carrier, s.site_id, si.address,
           si.latitude, si.longitude, s.overall_volume_m3, s.overall_predicted_fill_m3,
           b.id AS bin_id, b.waste_type, b.capacity_m3, sb.predicted_fill, sb.due
    FROM collection_stops AS s
    JOIN sites AS si ON si.id = s.site_id
    JOIN stop_bins AS sb ON sb.stop_id = s.id
    JOIN bins AS b ON b.id = sb.bin_id
    WHERE s.date = :day
      AND EXISTS (SELECT 1 FROM stop_bins AS d WHERE d.stop_id = s.id AND d.due)
    ORDER BY s.site_id, s.id, b.id
    """
)


@dataclass
class PlanSummary:
    evaluated: int
    due: int
    # Stops per waste carrier; the None key counts unassigned stops.
    stops_per_carrier: dict[str | None, int] = field(default_factory=dict)
    without_capacity: int = 0

    @property
    def unassigned_stops(self) -> int:
        return self.stops_per_carrier.get(None, 0)


def build_plan(session: Session, day: date, threshold: int) -> PlanSummary:
    """Replace the plan of `day` with stops for bins predicted above `threshold`.

    A stop is made for each (carrier, site) with a due bin and covers all of the carrier's
    bins there. Runs in the caller's session and commits once, so a failure leaves the
    previous plan of the date untouched.
    """
    session.execute(text(f"SET LOCAL lock_timeout = {SYNC_LOCK_TIMEOUT_MS}"))
    levels = predict_fill_levels(session, day)
    due_count = sum(level > threshold for level in levels.values())
    session.execute(CREATE_FILL_SQL)
    if levels:
        session.execute(
            text("INSERT INTO bin_fill (bin_id, predicted_fill, due) VALUES (:b, :f, :d)"),
            [{"b": bin_id, "f": level, "d": level > threshold} for bin_id, level in levels.items()],
        )
    session.execute(text("DELETE FROM collection_stops WHERE date = :day"), {"day": day})
    session.execute(INSERT_STOPS_SQL, {"day": day})
    session.execute(INSERT_STOP_BINS_SQL, {"day": day})
    stops = dict(session.execute(STOPS_PER_CARRIER_SQL, {"day": day}).all())
    without_capacity = session.execute(NO_CAPACITY_SQL, {"day": day}).scalar_one()
    session.commit()
    return PlanSummary(len(levels), due_count, stops, without_capacity)


def get_plan(
    session: Session, day: date, carriers: set[str | None] | list[str | None] | None = None
) -> dict[str | None, list[dict]]:
    """Return the stops of `day` grouped by waste carrier.

    The `None` key holds unassigned stops. With `carriers`, exactly those keys are
    returned (empty list when a carrier has no stops); pass `None` inside it to ask for
    the unassigned group. A date without a plan gives `{}` (or empty groups when
    carriers are requested). A stop lists all the carrier's bins at the site, with a `due`
    flag; stops without a due bin are skipped. Stops are ordered by site ID, bins by bin ID.
    """
    wanted = None if carriers is None else set(carriers)
    plan: dict[str | None, list[dict]] = {} if wanted is None else {c: [] for c in wanted}
    stops: dict[int, dict] = {}
    for row in session.execute(READ_SQL, {"day": day}).mappings():
        carrier = row["waste_carrier"]
        if wanted is not None and carrier not in wanted:
            continue
        stop = stops.get(row["stop_id"])
        if stop is None:
            stop = {
                "stop_id": row["stop_id"],
                "site_id": row["site_id"],
                "address": row["address"],
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "overall_volume_m3": row["overall_volume_m3"],
                "overall_predicted_fill_m3": row["overall_predicted_fill_m3"],
                "bins": [],
            }
            stops[row["stop_id"]] = stop
            plan.setdefault(carrier, []).append(stop)
        stop["bins"].append(
            {
                "bin_id": row["bin_id"],
                "waste_type": row["waste_type"],
                "capacity_m3": row["capacity_m3"],
                "predicted_fill": row["predicted_fill"],
                "due": row["due"],
            }
        )
    return plan
