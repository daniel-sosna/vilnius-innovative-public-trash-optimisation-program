import random
from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

MAX_FILL_LEVEL = 4


def predict_fill_levels(session: Session, day: date) -> dict[int, int]:
    """Return the predicted fill level of every stored bin on `day`.

    This is the contract the real fill-level model must fulfil: a dict
    `{bin_id: level}` with one entry per row of `bins` and an integer level from
    0 (empty) to 4 (full). Plan building, storage and reading depend only on it.

    MOCK: until the model exists, levels are synthetic, drawn uniformly from 0..4
    per bin in ID order from a generator seeded with the date. They are not observed
    or model-predicted data.
    """
    bin_ids = session.execute(text("SELECT id FROM bins ORDER BY id")).scalars()
    rng = random.Random(f"collection-plan:{day.isoformat()}")
    return {bin_id: rng.randint(0, MAX_FILL_LEVEL) for bin_id in bin_ids}
