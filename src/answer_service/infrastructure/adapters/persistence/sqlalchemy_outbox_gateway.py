import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Final, override
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from answer_service.application.common.ports.outbox import (
    OutboxCommandGateway,
    OutboxMessage,
)
from answer_service.infrastructure.errors import RepoError
from answer_service.infrastructure.persistence.models import (
    OutboxRecord,
    outbox_messages_table,
)

logger: Final[logging.Logger] = logging.getLogger(__name__)


class SqlAlchemyOutboxGateway(OutboxCommandGateway):
    def __init__(self, session: AsyncSession) -> None:
        self._session: Final[AsyncSession] = session

    @override
    async def add(self, message: OutboxMessage) -> None:
        self._session.add(
            OutboxRecord(
                id=message.id,
                event_type=message.event_type,
                payload=message.payload,
                created_at=message.created_at,
                processed_at=message.processed_at,
            ),
        )

    @override
    async def read_pending(self, limit: int) -> Sequence[OutboxMessage]:
        """Claims a batch of unprocessed rows for this transaction.

        ``FOR UPDATE ... SKIP LOCKED`` is what lets several relay replicas run
        at once: each locks the rows it takes until commit, and the others step
        over them instead of blocking or double-publishing.
        """
        stmt = (
            select(OutboxRecord)
            .where(outbox_messages_table.c.processed_at.is_(None))
            .order_by(outbox_messages_table.c.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        try:
            records = (await self._session.execute(stmt)).scalars().all()
        except SQLAlchemyError as e:
            msg = "Failed to read pending outbox messages."
            raise RepoError(msg) from e

        return [
            OutboxMessage(
                id=record.id,
                event_type=record.event_type,
                payload=record.payload,
                created_at=record.created_at,
                processed_at=record.processed_at,
            )
            for record in records
        ]

    @override
    async def mark_processed(self, message_id: UUID) -> None:
        stmt = (
            update(outbox_messages_table)
            .where(outbox_messages_table.c.id == message_id)
            .values(processed_at=datetime.now(UTC))
        )
        try:
            await self._session.execute(stmt)
        except SQLAlchemyError as e:
            msg = "Failed to mark the outbox message as processed."
            raise RepoError(msg) from e
