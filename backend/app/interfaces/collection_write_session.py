"""Writable collection-management transactions, separate from browsing snapshots."""

import logging
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def collection_write_session(request: Request) -> Iterator[Session]:
    try:
        with request.app.state.sessions() as session:
            try:
                session.execute(text("SET LOCAL statement_timeout = '5s'"))
                session.execute(text("SET LOCAL lock_timeout = '1s'"))
                yield session
            finally:
                session.rollback()
    except SQLAlchemyError as error:
        logger.error("Collection operation failed (%s)", type(error).__name__)
        raise HTTPException(status_code=500, detail="Collection operation failed") from None


CollectionWriteSession = Annotated[
    Session, Depends(collection_write_session, scope="function")
]
