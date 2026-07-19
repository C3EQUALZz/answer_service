import logging
from typing import Final, override

from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from answer_service.application.common.ports.gateways import IndexingTaskCommandGateway
from answer_service.domain.common.events_collection import EventsCollection
from answer_service.domain.indexing.entities.indexing_task import IndexingTask
from answer_service.domain.indexing.value_objects.task_id import TaskId
from answer_service.infrastructure.errors import RepoError
from answer_service.infrastructure.persistence.models import indexing_tasks_table

logger: Final[logging.Logger] = logging.getLogger(__name__)


class SqlAlchemyIndexingTaskGateway(IndexingTaskCommandGateway):
    def __init__(
        self,
        session: AsyncSession,
        events_collection: EventsCollection,
    ) -> None:
        self._session: Final[AsyncSession] = session
        self._events_collection: Final[EventsCollection] = events_collection

    @override
    async def add(self, task: IndexingTask) -> None:
        self._session.add(task)

    @override
    async def read_by_id(self, task_id: TaskId) -> IndexingTask | None:
        stmt = select(IndexingTask).where(indexing_tasks_table.c.id == task_id)
        try:
            task = (await self._session.execute(stmt)).scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.exception("failed to read the indexing task")
            msg = "Failed to read the indexing task."
            raise RepoError(msg) from e
        return self._inject(task) if task is not None else None

    @override
    async def update(self, task: IndexingTask) -> None:
        """No-op by design — see :meth:`SqlAlchemyQACatalogGateway.update`."""

    @override
    async def delete_by_id(self, task_id: TaskId) -> None:
        stmt = delete(indexing_tasks_table).where(indexing_tasks_table.c.id == task_id)
        try:
            await self._session.execute(stmt)
        except SQLAlchemyError as e:
            logger.exception("failed to delete the indexing task")
            msg = "Failed to delete the indexing task."
            raise RepoError(msg) from e

    def _inject(self, task: IndexingTask) -> IndexingTask:
        task.events_collection = self._events_collection
        return task
