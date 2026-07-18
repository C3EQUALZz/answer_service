from dataclasses import dataclass

from answer_service.application.common.mediator.markers import Command
from answer_service.domain.indexing.value_objects.task_id import TaskId


@dataclass(frozen=True, slots=True)
class MarkIndexingRunningCommand(Command[None]):
    """Mark a queued indexing task as running and commit it.

    Dispatched by the worker just before the heavy sync, in its own transaction,
    so the task-status API can show ``RUNNING`` while the work is in flight.
    """

    task_id: TaskId
