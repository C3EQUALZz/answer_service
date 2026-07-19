import logging
from typing import TYPE_CHECKING, Any, Final, override

from sqlalchemy import Row, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from answer_service.application.common.ports.gateways import (
    IndexingTaskQueryGateway,
    IndexingTaskView,
)
from answer_service.infrastructure.errors import RepoError
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

    def __init__(self, session: AsyncSession) -> None:
        self._session: Final[AsyncSession] = session

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

        return self._to_view(row) if row is not None else None

    @staticmethod
    def _to_view(row: Row[Any]) -> IndexingTaskView:
        stats = row.stats
        failure = row.failure
        return IndexingTaskView(
            task_id=row.id,
            status=row.status,
            source=str(row.source),
            created_at=row.created_at,
            started_at=row.started_at,
            finished_at=row.finished_at,
            created=stats.created,
            updated=stats.updated,
            deleted=stats.deleted,
            skipped=stats.skipped,
            failure_code=failure.code if failure is not None else None,
            failure_message=failure.message if failure is not None else None,
        )
