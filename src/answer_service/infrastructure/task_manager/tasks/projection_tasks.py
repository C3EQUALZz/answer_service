import logging
from typing import Final

from dishka import FromDishka
from dishka.integrations.taskiq import inject
from taskiq import AsyncBroker

from answer_service.application.commands.search.project_event.command import (
    ProjectEventCommand,
)
from answer_service.application.common.mediator.sender import Sender
from answer_service.application.common.ports.task_manager import ProjectEventPayload
from answer_service.application.common.ports.task_manager.task_keys import (
    OUTBOX_TASK_KEY,
)

logger: Final[logging.Logger] = logging.getLogger(__name__)

MAX_RETRIES: Final[int] = 5
RETRY_DELAY_SECONDS: Final[int] = 10


@inject(patch_module=True)
async def project_event_task(
    payload: ProjectEventPayload,
    sender: FromDishka[Sender],
) -> None:
    """Applies one relayed event to the search index.

    Retries on failure, unlike the indexing task: projection is idempotent, and
    a failure here is almost always the vector store being briefly unavailable
    rather than bad data. Giving up would leave the index permanently behind the
    catalog with nothing to notice it.
    """
    await sender.send(
        ProjectEventCommand(
            message_id=payload.message_id,
            event_type=payload.event_type,
            payload=payload.payload,
        ),
    )


def setup_projection_tasks(broker: AsyncBroker) -> None:
    broker.register_task(
        func=project_event_task,
        task_name=str(OUTBOX_TASK_KEY),
        retry_on_error=True,
        max_retries=MAX_RETRIES,
        delay=RETRY_DELAY_SECONDS,
    )
