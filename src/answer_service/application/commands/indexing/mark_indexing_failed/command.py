from dataclasses import dataclass

from answer_service.application.common.mediator.markers import Command
from answer_service.domain.indexing.value_objects.task_id import TaskId


@dataclass(frozen=True, slots=True)
class MarkIndexingFailedCommand(Command[None]):
    """Record why an indexing run ended unsuccessfully.

    Dispatched by the worker from its error path, in its own transaction, so the
    ``FAILED`` status survives the rollback of the work that raised. Carries the
    reason as plain strings — the handler turns them into the domain value object.
    """

    task_id: TaskId
    code: str
    message: str
