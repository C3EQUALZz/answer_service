import logging
from typing import TYPE_CHECKING, Final, override

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from answer_service.application.common.ports.gateways import (
    IndexingTaskQueryGateway,
    IndexingTaskView,
)
from answer_service.infrastructure.errors import RepoError
from answer_service.infrastructure.mappers.indexing_task_view_mapper import (
    IndexingTaskViewMapper,
)
from answer_service.infrastructure.persistence.models import indexing_tasks_table

if TYPE_CHECKING:
    from answer_service.domain.indexing.value_objects.task_id import TaskId

logger: Final[logging.Logger] = logging.getLogger(__name__)


class SqlAlchemyIndexingTaskQueryGateway(IndexingTaskQueryGateway):
    """Reads task status as columns, never as an aggregate.

    Clients poll this while a sync runs, so it stays a plain row read: no state
    machine is reconstructed, and nothing it returns can be mistaken for
    something writable.
    """

    def __init__(
        self,
        session: AsyncSession,
        view_mapper: IndexingTaskViewMapper,
    ) -> None:
        self._session: Final[AsyncSession] = session
        self._view_mapper: Final[IndexingTaskViewMapper] = view_mapper

    @override
    async def read_by_id(self, task_id: TaskId) -> IndexingTaskView | None:
        stmt = select(
            indexing_tasks_table.c.id,
            indexing_tasks_table.c.status,
            indexing_tasks_table.c.source,
            indexing_tasks_table.c.created_at,
            indexing_tasks_table.c.started_at,
            indexing_tasks_table.c.finished_at,
            indexing_tasks_table.c.stats,
            indexing_tasks_table.c.failure,
        ).where(indexing_tasks_table.c.id == task_id)

        try:
            row = (await self._session.execute(stmt)).one_or_none()
        except SQLAlchemyError as e:
            logger.exception("failed to read the indexing task status")
            msg = "Failed to read the indexing task status."
            raise RepoError(msg) from e

        return self._view_mapper.to_view(row) if row is not None else None
