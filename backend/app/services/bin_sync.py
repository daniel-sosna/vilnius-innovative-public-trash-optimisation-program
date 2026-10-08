import logging
from dataclasses import dataclass

from app.core.config import Settings
from app.infrastructure.database import SYNC_LOCK_TIMEOUT_MS, SYNC_STATEMENT_TIMEOUT_MS
from app.infrastructure.models import Bin
from app.integrations.vilnius_gis import fetch_bins
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger(__name__)
UPSERT_BATCH_SIZE = 1_000


class BinSyncError(Exception):
    pass


@dataclass(frozen=True)
class SyncSummary:
    retrieved: int
    skipped: int
    upserted: int


def synchronize_bins(
    settings: Settings, sessions: sessionmaker[Session]
) -> SyncSummary:
    logger.info("Starting bin synchronization")
    try:
        snapshot = fetch_bins(
            str(settings.bin_sync_source_url), settings.bin_sync_http_timeout_seconds
        )
    except Exception as error:
        raise BinSyncError(f"GIS retrieval/validation failed: {error}") from error

    if not snapshot.bins:
        logger.warning(
            "GIS collection contains no usable features; keeping existing bins"
        )
    else:
        try:
            with sessions.begin() as session:
                session.execute(
                    text(f"SET LOCAL statement_timeout = {SYNC_STATEMENT_TIMEOUT_MS}")
                )
                session.execute(
                    text(f"SET LOCAL lock_timeout = {SYNC_LOCK_TIMEOUT_MS}")
                )
                for offset in range(0, len(snapshot.bins), UPSERT_BATCH_SIZE):
                    statement = insert(Bin).values(
                        snapshot.bins[offset : offset + UPSERT_BATCH_SIZE]
                    )
                    session.execute(
                        statement.on_conflict_do_update(
                            index_elements=[Bin.id],
                            set_={
                                "lat": statement.excluded.lat,
                                "lon": statement.excluded.lon,
                                "address": statement.excluded.address,
                                "type": statement.excluded.type,
                                "greening": statement.excluded.greening,
                            },
                        )
                    )
        except SQLAlchemyError as error:
            original = getattr(error, "orig", error)
            diagnostic = getattr(original, "diag", None)
            reason = (
                getattr(diagnostic, "message_primary", None) or type(original).__name__
            )
            raise BinSyncError(
                f"database write failed; transaction rolled back: {reason}"
            ) from error

    summary = SyncSummary(snapshot.retrieved, snapshot.skipped, len(snapshot.bins))
    logger.info(
        "Bin synchronization complete: retrieved=%s skipped=%s upserted=%s",
        summary.retrieved,
        summary.skipped,
        summary.upserted,
    )
    return summary
