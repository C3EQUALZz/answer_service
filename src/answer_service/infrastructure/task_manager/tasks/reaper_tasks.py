import logging
from typing import Final

from dishka import FromDishka
from dishka.integrations.taskiq import inject
from taskiq import AsyncBroker

from answer_service.application.commands.indexing.reap_stuck_tasks.command import (
    ReapStuckTasksCommand,
)
from answer_service.application.common.mediator.sender import Sender
from answer_service.application.common.ports.task_manager.task_keys import (
    REAP_STUCK_TASKS_TASK_NAME,
)

logger: Final[logging.Logger] = logging.getLogger(__name__)

REAPER_CRON: Final[str] = "*/10 * * * *"
MAX_RETRIES: Final[int] = 3
RETRY_DELAY_SECONDS: Final[int] = 30


@inject(patch_module=True)
async def reap_stuck_tasks_task(sender: FromDishka[Sender]) -> None:
    """Settles indexing runs abandoned by a dead worker, every ten minutes.

    Ten rather than every minute because nothing here is urgent: the tasks it
    settles have been stuck for an hour already, and a tighter tick would only
    add empty transactions.
    """
    response = await sender.send(ReapStuckTasksCommand())
    if response.reaped:
        logger.warning("reap_stuck_tasks: settled %d abandoned run(s)", response.reaped)


def setup_reaper_tasks(broker: AsyncBroker) -> None:
    broker.register_task(
        func=reap_stuck_tasks_task,
        task_name=REAP_STUCK_TASKS_TASK_NAME,
        schedule=[{"cron": REAPER_CRON}],
        retry_on_error=True,
        max_retries=MAX_RETRIES,
        delay=RETRY_DELAY_SECONDS,
    )
