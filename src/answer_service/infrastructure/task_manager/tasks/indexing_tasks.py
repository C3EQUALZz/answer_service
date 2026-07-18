import logging
from typing import Final

from dishka import FromDishka
from dishka.integrations.taskiq import inject
from taskiq import AsyncBroker

from answer_service.application.commands.indexing.mark_indexing_failed.command import (
    MarkIndexingFailedCommand,
)
from answer_service.application.commands.indexing.mark_indexing_running.command import (
    MarkIndexingRunningCommand,
)
from answer_service.application.commands.indexing.run_indexing.command import (
    RunIndexingCommand,
)
from answer_service.application.common.mediator.sender import Sender
from answer_service.application.common.ports.task_manager import RunIndexingPayload
from answer_service.application.common.ports.task_manager.task_keys import (
    INDEXING_TASK_KEY,
)
from answer_service.domain.common.error import AppError
from answer_service.domain.indexing.value_objects.task_id import TaskId

logger: Final[logging.Logger] = logging.getLogger(__name__)


@inject(patch_module=True)
async def run_indexing_task(
    payload: RunIndexingPayload,
    sender: FromDishka[Sender],
) -> None:
    """Runs one synchronization, recording the outcome on the task either way.

    Three commands, three transactions, on purpose: ``RUNNING`` is committed
    before the long work so the status API can show it, the work itself commits
    or rolls back as one unit, and the failure record is written afterwards so
    it survives that rollback.

    The failure is *not* re-raised. Recording it moves the task to a terminal
    state, so a taskiq retry would find a task it is no longer allowed to
    complete and fail on the state machine instead of on the real cause.
    Retrying a genuinely transient failure is a decision for the caller, who
    enqueues a new task.
    """
    task_id = TaskId(payload.task_id)

    await sender.send(MarkIndexingRunningCommand(task_id=task_id))

    try:
        await sender.send(RunIndexingCommand(task_id=task_id))
    except AppError as error:
        logger.exception("run_indexing: task %s failed", task_id)
        await sender.send(
            MarkIndexingFailedCommand(
                task_id=task_id,
                code=type(error).__name__,
                message=str(error),
            ),
        )


def setup_indexing_tasks(broker: AsyncBroker) -> None:
    broker.register_task(
        func=run_indexing_task,
        task_name=str(INDEXING_TASK_KEY),
    )
