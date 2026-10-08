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
