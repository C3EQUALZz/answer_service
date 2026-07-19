import logging
from typing import TYPE_CHECKING, Final, final

from answer_service.domain.common.events_collection import EventsCollection
from answer_service.domain.indexing.entities.indexing_task import IndexingTask
from answer_service.domain.indexing.ports.id_generator import TaskIdGenerator

if TYPE_CHECKING:
    from answer_service.domain.indexing.value_objects.source_reference import (
        SourceReference,
    )


logger: Final[logging.Logger] = logging.getLogger(__name__)


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

    def create(self, source: SourceReference) -> IndexingTask:
        task = IndexingTask.queue(
            task_id=self._task_id_generator(),
            source=source,
            events_collection=self._events_collection,
        )
        logger.debug("indexing_task_factory: queued task %s for %s", task.id, source)
        return task
