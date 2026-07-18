import logging
from typing import Final, override

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from answer_service.application.common.ports.transaction_manager import (
    TransactionManager,
)
from answer_service.infrastructure.errors import RepoError

logger: Final[logging.Logger] = logging.getLogger(__name__)


class SqlAlchemyTransactionManager(TransactionManager):
    """Unit of work over the request-scoped session, driven by the pipeline."""

    def __init__(self, session: AsyncSession) -> None:
        self._session: Final[AsyncSession] = session

    @override
    async def flush(self) -> None:
        try:
            await self._session.flush()
        except SQLAlchemyError as e:
            msg = "Failed to flush the session."
            raise RepoError(msg) from e

    @override
    async def commit(self) -> None:
        try:
            await self._session.commit()
        except SQLAlchemyError as e:
            msg = "Failed to commit the transaction."
            raise RepoError(msg) from e

    @override
    async def rollback(self) -> None:
        try:
            await self._session.rollback()
        except SQLAlchemyError as e:
            msg = "Failed to roll back the transaction."
            raise RepoError(msg) from e
