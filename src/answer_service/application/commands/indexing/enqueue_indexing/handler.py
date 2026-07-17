from typing import Final, override

from answer_service.application.commands.indexing.enqueue_indexing.command import (
    EnqueueIndexingCommand,
    EnqueueIndexingResponse,
)
from answer_service.application.common.mediator.handlers import CommandHandler
from answer_service.application.common.ports.gateways import IndexingTaskCommandGateway
from answer_service.application.common.ports.source_file.source_file_reader import (
    SourceFileReader,
)
from answer_service.application.common.ports.source_file.source_file_storage import (
    SourceFileStorage,
)
from answer_service.application.common.ports.task_manager import RunIndexingPayload
from answer_service.application.common.ports.task_manager.task_id import TaskKey
from answer_service.application.common.ports.task_manager.task_manager import (
    TaskScheduler,
)
from answer_service.domain.indexing.factories.indexing_task_factory import (
    IndexingTaskFactory,
)

_INDEXING_TASK_KEY: Final[TaskKey] = TaskKey("indexing")


class EnqueueIndexingHandler(
    CommandHandler[EnqueueIndexingCommand, EnqueueIndexingResponse],
):
    def __init__(
        self,
        source_reader: SourceFileReader,
        source_storage: SourceFileStorage,
        task_factory: IndexingTaskFactory,
        task_gateway: IndexingTaskCommandGateway,
        task_scheduler: TaskScheduler,
    ) -> None:
        self._source_reader: Final[SourceFileReader] = source_reader
        self._source_storage: Final[SourceFileStorage] = source_storage
        self._task_factory: Final[IndexingTaskFactory] = task_factory
        self._task_gateway: Final[IndexingTaskCommandGateway] = task_gateway
        self._task_scheduler: Final[TaskScheduler] = task_scheduler

    @override
    async def handle(
        self,
        command: EnqueueIndexingCommand,
    ) -> EnqueueIndexingResponse:
        # Fail fast on a malformed file before persisting or scheduling anything.
        await self._source_reader.validate(
            content=command.content,
            filename=command.filename,
        )
        source = await self._source_storage.save(
            content=command.content,
            filename=command.filename,
        )

        task = self._task_factory.create(source=source)
        await self._task_gateway.add(task)

        background_task_id = self._task_scheduler.make_task_id(
            _INDEXING_TASK_KEY,
            task.id,
        )
        await self._task_scheduler.schedule(
            background_task_id,
            RunIndexingPayload(task_id=task.id),
        )

        return EnqueueIndexingResponse(task_id=task.id, status=task.status)
