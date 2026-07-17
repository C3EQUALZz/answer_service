from dataclasses import dataclass

from answer_service.application.common.mediator.markers import Command
from answer_service.domain.indexing.value_objects.task_id import TaskId
from answer_service.domain.indexing.value_objects.task_status import IndexingTaskStatus


@dataclass(frozen=True, slots=True)
class EnqueueIndexingResponse:
    task_id: TaskId
    status: IndexingTaskStatus


@dataclass(frozen=True, slots=True)
class EnqueueIndexingCommand(Command[EnqueueIndexingResponse]):
    """Upload a source file and schedule its synchronization.

    The file is validated (format + required columns) synchronously for
    fail-fast feedback; the heavy parse / diff / index runs in the background.
    """

    content: bytes
    filename: str
    content_type: str | None = None
