import logging
from typing import Final

from dishka import FromDishka
from dishka.integrations.taskiq import inject
from taskiq import AsyncBroker

from answer_service.application.commands.outbox.relay_outbox.command import (
    RelayOutboxCommand,
)
from answer_service.application.common.mediator.sender import Sender
from answer_service.application.common.ports.task_manager.task_keys import (
    RELAY_OUTBOX_TASK_NAME,
)

logger: Final[logging.Logger] = logging.getLogger(__name__)

RELAY_CRON: Final[str] = "* * * * *"
MAX_RETRIES: Final[int] = 3
RETRY_DELAY_SECONDS: Final[int] = 15


@inject(patch_module=True)
async def relay_outbox_task(sender: FromDishka[Sender]) -> None:
    """Drains a batch of pending outbox messages once a minute.

    Safe to retry and safe to run on several replicas: the gateway claims rows
    with ``SKIP LOCKED``, and a message is marked processed only after it was
    handed to the transport.
    """
    response = await sender.send(RelayOutboxCommand())
    if response.total:
        logger.info(
            "relay_outbox: published %d of %d",
            response.published,
            response.total,
        )


def setup_outbox_tasks(broker: AsyncBroker) -> None:
    broker.register_task(
        func=relay_outbox_task,
        task_name=RELAY_OUTBOX_TASK_NAME,
        schedule=[{"cron": RELAY_CRON}],
        retry_on_error=True,
        max_retries=MAX_RETRIES,
        delay=RETRY_DELAY_SECONDS,
    )
