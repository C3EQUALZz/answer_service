from abc import abstractmethod
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
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
    async def delete_by_id(self, task_id: TaskId) -> None:
        raise NotImplementedError
