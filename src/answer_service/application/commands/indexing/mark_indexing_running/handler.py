from typing import Final, override

from answer_service.application.commands.indexing.mark_indexing_running.command import (
    MarkIndexingRunningCommand,
)
from answer_service.application.common.mediator.handlers import CommandHandler
from answer_service.application.common.ports.gateways import IndexingTaskCommandGateway
from answer_service.application.error import IndexingTaskNotFoundError


class MarkIndexingRunningHandler(CommandHandler[MarkIndexingRunningCommand, None]):
    def __init__(self, task_gateway: IndexingTaskCommandGateway) -> None:
        self._task_gateway: Final[IndexingTaskCommandGateway] = task_gateway

    @override
    async def handle(self, command: MarkIndexingRunningCommand) -> None:
        task = await self._task_gateway.read_by_id(command.task_id)
        if task is None:
            msg = f"Indexing task '{command.task_id}' not found."
            raise IndexingTaskNotFoundError(msg)

        task.start()
        await self._task_gateway.update(task)
