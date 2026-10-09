"""Short writable transactions for public resident reports."""

import logging
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def resident_request_session(request: Request) -> Iterator[Session]:
    try:
        with request.app.state.sessions() as session:
            try:
                session.execute(text("SET LOCAL statement_timeout = '5s'"))
                session.execute(text("SET LOCAL lock_timeout = '1s'"))
                yield session
            finally:
                session.rollback()
    except SQLAlchemyError as error:
        logger.error("Resident request failed (%s)", type(error).__name__)
        raise HTTPException(status_code=500, detail="Resident request failed") from None


ResidentRequestSession = Annotated[
    Session, Depends(resident_request_session, scope="function")
]
