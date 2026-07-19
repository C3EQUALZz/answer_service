from abc import abstractmethod
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime

    from answer_service.domain.indexing.entities.indexing_task import IndexingTask
    from answer_service.domain.indexing.value_objects.task_id import TaskId


class IndexingTaskCommandGateway(Protocol):
    """Write-side persistence for :class:`IndexingTask`."""

    @abstractmethod
    async def add(self, task: IndexingTask) -> None:
        raise NotImplementedError

    @abstractmethod
    async def read_by_id(self, task_id: TaskId) -> IndexingTask | None:
        raise NotImplementedError

    @abstractmethod
    async def update(self, task: IndexingTask) -> None:
        raise NotImplementedError

    @abstractmethod
    async def read_stuck(
        self,
        *,
        started_before: datetime,
        limit: int,
    ) -> Sequence[IndexingTask]:
        """Claims running tasks that started before *started_before*.

        A task reaches ``RUNNING`` in a transaction of its own, so a worker that
        dies mid-run leaves it there with nobody to settle it. Nothing times it
        out — the status endpoint would report ``RUNNING`` forever.
        """
        raise NotImplementedError

    @abstractmethod
    async def delete_by_id(self, task_id: TaskId) -> None:
        raise NotImplementedError
