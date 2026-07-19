import logging
from typing import Final, override

from answer_service.application.commands.indexing.mark_indexing_running.command import (
    MarkIndexingRunningCommand,
)
from answer_service.application.common.mediator.handlers import CommandHandler
from answer_service.application.common.ports.gateways import IndexingTaskCommandGateway
from answer_service.application.error import IndexingTaskNotFoundError
from answer_service.domain.indexing.value_objects.task_status import IndexingTaskStatus

logger: Final[logging.Logger] = logging.getLogger(__name__)


class MarkIndexingRunningHandler(CommandHandler[MarkIndexingRunningCommand, None]):
    """Fixes the ``RUNNING`` state of a queued task before the heavy sync starts.

    Tolerates a task that is no longer ``QUEUED``: the worker's message is
    delivered at least once, and a redelivery must not fail on a state machine
    that has already moved on. Only a genuinely queued task is transitioned.
    """

    def __init__(self, task_gateway: IndexingTaskCommandGateway) -> None:
        self._task_gateway: Final[IndexingTaskCommandGateway] = task_gateway

    @override
    async def handle(self, command: MarkIndexingRunningCommand) -> None:
        logger.info("mark_indexing_running: task %s", command.task_id)

        task = await self._task_gateway.read_by_id(command.task_id)
        if task is None:
            logger.warning(
                "mark_indexing_running: task %s not found",
                command.task_id,
            )
            msg = f"Indexing task '{command.task_id}' not found."
            raise IndexingTaskNotFoundError(msg)

        if task.status is not IndexingTaskStatus.QUEUED:
            logger.info(
                "mark_indexing_running: task %s is already %s, leaving it alone",
                command.task_id,
                task.status,
            )
            return

        task.start()
        await self._task_gateway.update(task)
        logger.info("mark_indexing_running: task %s is now running", command.task_id)
