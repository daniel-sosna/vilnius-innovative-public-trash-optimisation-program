from app.core.config import Settings
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

CONNECT_TIMEOUT_SECONDS = 10
SYNC_STATEMENT_TIMEOUT_MS = 30_000
SYNC_LOCK_TIMEOUT_MS = 5_000


def create_database_engine(settings: Settings) -> Engine:
    return create_engine(
        settings.database_url,
        connect_args={
            "connect_timeout": CONNECT_TIMEOUT_SECONDS,
            "options": "-c timezone=UTC",
        },
        pool_pre_ping=True,
        hide_parameters=True,
    )


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine)


def create_analytics_engine(settings: Settings) -> Engine:
    # Separate bounded acquisition; no pre-ping/network wait outside query deadlines.
    return create_engine(settings.database_url, connect_args={
        "connect_timeout": 1,
        "options": "-c default_transaction_read_only=on -c statement_timeout=5000 -c lock_timeout=1000",
    }, pool_timeout=1, hide_parameters=True)
