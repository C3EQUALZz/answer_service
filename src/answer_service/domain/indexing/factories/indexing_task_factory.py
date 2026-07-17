from typing import Final, final

from answer_service.domain.common.events_collection import EventsCollection
from answer_service.domain.indexing.entities.indexing_task import IndexingTask
from answer_service.domain.indexing.ports.id_generator import TaskIdGenerator


@final
class IndexingTaskFactory:
    """Domain factory for the :class:`IndexingTask` aggregate.

    Receives the request-scoped ``EventsCollection`` and a ``TaskIdGenerator``
    port via DI, so the domain never depends on how ids are produced.
    """

    def __init__(
        self,
        events_collection: EventsCollection,
        task_id_generator: TaskIdGenerator,
    ) -> None:
        self._events_collection: Final[EventsCollection] = events_collection
        self._task_id_generator: Final[TaskIdGenerator] = task_id_generator

    def create(self) -> IndexingTask:
        return IndexingTask.queue(
            task_id=self._task_id_generator(),
            events_collection=self._events_collection,
        )
