"""Short read-only snapshots for collection browsing, independent of Trucks."""

import logging
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def collection_session(request: Request) -> Iterator[Session]:
    try:
        with request.app.state.sessions() as session:
            try:
                session.execute(
                    text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
                )
                session.execute(text("SET LOCAL statement_timeout = '5s'"))
                session.execute(text("SET LOCAL lock_timeout = '1s'"))
                yield session
            finally:
                session.rollback()
    except SQLAlchemyError as error:
        # Include setup/rollback/close failures, without SQL or credentials.
        logger.error("Collection read failed (%s)", type(error).__name__)
        raise HTTPException(status_code=500, detail="Collection read failed") from None


# Release the snapshot after response construction, before sending the response.
CollectionSession = Annotated[Session, Depends(collection_session, scope="function")]
