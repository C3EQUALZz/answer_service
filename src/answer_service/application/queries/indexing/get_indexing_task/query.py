from dataclasses import dataclass

from answer_service.application.common.mediator.markers import Query
from answer_service.application.common.ports.gateways import IndexingTaskView
from answer_service.domain.indexing.value_objects.task_id import TaskId


@dataclass(frozen=True, slots=True)
class GetIndexingTaskQuery(Query[IndexingTaskView]):
    """Reads the current state of one indexing run.

    Backs the status endpoint clients poll after uploading a file.
    """

    task_id: TaskId
