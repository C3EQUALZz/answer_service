import logging
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
from answer_service.domain.indexing.factories.indexing_task_factory import (
    IndexingTaskFactory,
)

logger: Final[logging.Logger] = logging.getLogger(__name__)


class EnqueueIndexingHandler(
    CommandHandler[EnqueueIndexingCommand, EnqueueIndexingResponse],
):
    def __init__(
        self,
        source_reader: SourceFileReader,
        source_storage: SourceFileStorage,
        task_factory: IndexingTaskFactory,
        task_gateway: IndexingTaskCommandGateway,
    ) -> None:
        self._source_reader: Final[SourceFileReader] = source_reader
        self._source_storage: Final[SourceFileStorage] = source_storage
        self._task_factory: Final[IndexingTaskFactory] = task_factory
        self._task_gateway: Final[IndexingTaskCommandGateway] = task_gateway

    @override
    async def handle(
        self,
        command: EnqueueIndexingCommand,
    ) -> EnqueueIndexingResponse:
        logger.info(
            "enqueue_indexing: received '%s' (%d bytes)",
            command.filename,
            len(command.content),
        )

        await self._source_reader.validate(
            content=command.content,
            filename=command.filename,
        )
        logger.info("enqueue_indexing: '%s' passed validation", command.filename)

        source = await self._source_storage.save(
            content=command.content,
            filename=command.filename,
        )
        logger.info("enqueue_indexing: staged '%s' at %s", command.filename, source)

        task = self._task_factory.create(source=source)
        await self._task_gateway.add(task)
        logger.info(
            "enqueue_indexing: queued task %s with status %s",
            task.id,
            task.status,
        )

        return EnqueueIndexingResponse(task_id=task.id, status=task.status)
