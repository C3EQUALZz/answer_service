import logging
from typing import Final, override

from answer_service.application.commands.indexing.mark_indexing_failed.command import (
    MarkIndexingFailedCommand,
)
from answer_service.application.common.mediator.handlers import CommandHandler
from answer_service.application.common.ports.gateways import IndexingTaskCommandGateway
from answer_service.application.error import IndexingTaskNotFoundError
from answer_service.domain.indexing.value_objects.failure_info import FailureInfo

logger: Final[logging.Logger] = logging.getLogger(__name__)


class MarkIndexingFailedHandler(CommandHandler[MarkIndexingFailedCommand, None]):
    """Fixes the terminal ``FAILED`` state of a task whose run was rolled back.

    Runs in a transaction of its own: the work done by ``run_indexing`` is gone by
    the time this executes, and only the task row is touched here. Tolerates a
    task that already reached a terminal state, so the worker may retry this step
    without turning a delivery retry into a second, unrelated failure.
    """

    def __init__(self, task_gateway: IndexingTaskCommandGateway) -> None:
        self._task_gateway: Final[IndexingTaskCommandGateway] = task_gateway

    @override
    async def handle(self, command: MarkIndexingFailedCommand) -> None:
        logger.info(
            "mark_indexing_failed: task %s, code=%s message=%s",
            command.task_id,
            command.code,
            command.message,
        )

        task = await self._task_gateway.read_by_id(command.task_id)
        if task is None:
            logger.warning(
                "mark_indexing_failed: task %s not found",
                command.task_id,
            )
            msg = f"Indexing task '{command.task_id}' not found."
            raise IndexingTaskNotFoundError(msg)

        if task.status.is_terminal:
            logger.info(
                "mark_indexing_failed: task %s already settled as %s",
                command.task_id,
                task.status,
            )
            return

        task.fail(FailureInfo(code=command.code, message=command.message))
        await self._task_gateway.update(task)
        logger.info("mark_indexing_failed: task %s marked failed", command.task_id)
