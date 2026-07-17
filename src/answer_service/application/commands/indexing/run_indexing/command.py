from dataclasses import dataclass

from answer_service.application.common.mediator.markers import Command
from answer_service.domain.indexing.value_objects.task_id import TaskId


@dataclass(frozen=True, slots=True)
class RunIndexingCommand(Command[None]):
    """Execute a scheduled synchronization run (dispatched by the worker).

    Picks up the already-persisted ``IndexingTask`` by id, reads its source and
    records the outcome against it.
    """

    task_id: TaskId
