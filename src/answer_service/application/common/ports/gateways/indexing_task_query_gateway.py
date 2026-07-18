from abc import abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from answer_service.domain.indexing.value_objects.task_id import TaskId
from answer_service.domain.indexing.value_objects.task_status import IndexingTaskStatus


@dataclass(frozen=True, slots=True)
class IndexingTaskView:
    """A task as the status endpoint reports it.

    A read model, not the aggregate: callers poll this, and rebuilding the whole
    aggregate — with its state machine — to render a status line would couple
    the API to rules it has no business enforcing.
    """

    task_id: TaskId
    status: IndexingTaskStatus
    source: str
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    created: int
    updated: int
    deleted: int
    skipped: int
    failure_code: str | None
    failure_message: str | None

    @property
    def is_finished(self) -> bool:
        return self.status.is_terminal


class IndexingTaskQueryGateway(Protocol):
    """Read-side access to indexing task status."""

    @abstractmethod
    async def read_by_id(self, task_id: TaskId) -> IndexingTaskView | None:
        raise NotImplementedError
