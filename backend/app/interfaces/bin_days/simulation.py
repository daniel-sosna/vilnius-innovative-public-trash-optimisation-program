"""Synthetic collection simulation for one bin: schedule cycle, attempts, look-back features."""

import random
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, timedelta

import holidays

WARMUP_DAYS = 35
WINDOW = 28
SINGLE_DATE_CYCLE = 28
MAX_PROBABILITY = 0.95
CYCLES = (1, 7, 14, 21, 28)


@dataclass(frozen=True)
class Parameters:
    seed: int
    p_first: float
    p_retry1: float
    p_retry2: float
    holiday_factor: float


def detect_cycle(planned: set[date]) -> tuple[int, frozenset[int]]:
    """Return (cycle length, residues of date.toordinal() % cycle that are planned days)."""
    if len(planned) == 1:
        return SINGLE_DATE_CYCLE, frozenset(d.toordinal() % SINGLE_DATE_CYCLE for d in planned)
    first = min(planned).replace(day=1)
    last = max(planned)
    last = (last.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    span = [first + timedelta(days=i) for i in range((last - first).days + 1)]
    for cycle in CYCLES:
        residues = frozenset(d.toordinal() % cycle for d in planned)
        if all(((d.toordinal() % cycle) in residues) == (d in planned) for d in span):
            return cycle, residues
    return SINGLE_DATE_CYCLE, frozenset(d.toordinal() % SINGLE_DATE_CYCLE for d in planned)


def holiday_ordinals(first: date, last: date) -> frozenset[int]:
    """Lithuanian public holidays, as ordinals, for the years touched by first..last."""
    calendar = holidays.country_holidays("LT", years=range(first.year, last.year + 1))
    return frozenset(d.toordinal() for d in calendar)


def simulate_bin(
    bin_id: int,
    planned: set[date],
    start: date,
    end: date,
    params: Parameters,
    holiday_days: frozenset[int],
) -> Iterator[tuple[date, str, int, int, int]]:
    """Yield (date, status, holidays_since_last_collection, collections_28d, missed_28d).

    Walks day by day from start - WARMUP_DAYS; only rows from start on are yielded. The
    look-back features describe the state at the start of the day, before its own outcome.
    """
    cycle, residues = detect_cycle(planned)
    rng = random.Random(f"{params.seed}:{bin_id}")
    first_ordinal = start.toordinal() - WARMUP_DAYS
    start_ordinal = start.toordinal()
    probabilities = (params.p_first, params.p_retry1, params.p_retry2)
    collected_ring = [0] * WINDOW
    missed_ring = [0] * WINDOW
    collections = missed = 0
    since_holidays = 0
    pending = 0  # 0: no retry pending, 1 or 2: the retry that is due today
    for ordinal in range(first_ordinal, end.toordinal() + 1):
        features = (since_holidays, collections, missed)
        is_holiday = ordinal in holiday_days
        if ordinal % cycle in residues:
            attempt = 0
        elif pending:
            attempt = pending
        else:
            attempt = -1
        success = fail_final = False
        status = "none"
        if attempt >= 0:
            probability = probabilities[attempt]
            if is_holiday:
                probability = min(probability * params.holiday_factor, MAX_PROBABILITY)
            if rng.random() < probability:
                retry_follows = attempt < 2 and (ordinal + 1) % cycle not in residues
                if retry_follows:
                    status = "failed"
                    pending = attempt + 1
                else:
                    status = "missed"
                    fail_final = True
                    pending = 0
            else:
                status = "collected" if attempt == 0 else "retry_collected"
                success = True
                pending = 0
        if ordinal >= start_ordinal:
            yield (date.fromordinal(ordinal), status, *features)
        slot = ordinal % WINDOW
        collections += success - collected_ring[slot]
        missed += fail_final - missed_ring[slot]
        collected_ring[slot] = success
        missed_ring[slot] = fail_final
        if success:
            since_holidays = 0
        elif is_holiday:
            since_holidays += 1
