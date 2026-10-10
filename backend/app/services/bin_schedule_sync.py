"""Manual refresh of VASA planned collection dates, one transaction per bin."""

import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from app.core.config import Settings
from app.infrastructure.models import Bin, BinSchedule
from app.integrations.vasa import VasaClient
from app.services.bin_sync import bounded_responses, transaction
from sqlalchemy import delete, insert, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger(__name__)
B, S = Bin.__table__, BinSchedule.__table__


class NoBinsError(Exception):
    pass


@dataclass
class ScheduleSummary:
    processed: int = 0
    with_dates: int = 0
    empty: int = 0
    failed: list[int] = field(default_factory=list)
    dates_stored: int = 0


def synchronize_schedules(
    settings: Settings,
    sessions: sessionmaker[Session],
    workers: int = 4,
    max_bins: int = 0,
) -> ScheduleSummary:
    query = select(B.c.id, B.c.external_id).order_by(B.c.id)
    if max_bins:
        query = query.limit(max_bins)
    with sessions() as session:
        bins = [tuple(row) for row in session.execute(query)]
    if not bins:
        raise NoBinsError("no bins are stored; import collection data first")

    client = VasaClient(settings)
    summary = ScheduleSummary()
    with ThreadPoolExecutor(workers) as pool:
        for (bin_id, identity), dates, error in bounded_responses(
            pool, bins, lambda item: client.schedule(item[1]), workers
        ):
            summary.processed += 1
            if error is None:
                try:
                    with transaction(sessions) as session:
                        session.execute(delete(S).where(S.c.bin_id == bin_id))
                        if dates:
                            session.execute(
                                insert(S),
                                [{"bin_id": bin_id, "date": day} for day in dates],
                            )
                except SQLAlchemyError as failure:
                    error = failure
            if error is not None:
                reason = (
                    type(getattr(error, "orig", error)).__name__
                    if isinstance(error, SQLAlchemyError)
                    else str(error)
                )
                logger.warning("bin=%s: schedule not stored: %s", identity, reason)
                summary.failed.append(identity)
            elif dates:
                summary.with_dates += 1
                summary.dates_stored += len(dates)
            else:
                summary.empty += 1
            if summary.processed % 1000 == 0:
                logger.info("Processed %d/%d bins", summary.processed, len(bins))
    return summary
