import logging
from typing import Final

from dishka import FromDishka
from dishka.integrations.taskiq import inject
from taskiq import AsyncBroker

from answer_service.application.commands.search.remove_qa_pair.command import (
    RemoveQAPairCommand,
)
from answer_service.application.commands.search.upsert_qa_pair.command import (
    UpsertQAPairCommand,
)
from answer_service.application.common.mediator.sender import Sender
from answer_service.application.common.ports.task_manager import (
    OutboxEventPayload,
    QAPairEventBody,
)
from answer_service.domain.indexing.events import (
    QAPairAdded,
    QAPairContentUpdated,
    QAPairRemoved,
)
from answer_service.domain.indexing.value_objects.external_id import ExternalId

logger: Final[logging.Logger] = logging.getLogger(__name__)

MAX_RETRIES: Final[int] = 5
RETRY_DELAY_SECONDS: Final[int] = 10


@inject(patch_module=True)
async def upsert_qa_pair_task(
    payload: OutboxEventPayload[QAPairEventBody],
    sender: FromDishka[Sender],
) -> None:
    """Applies a created or changed pair to the search index."""
    external_id = payload.body.external_id.value
    logger.info(
        "upsert_qa_pair_task: %s for '%s' (message %s)",
        payload.event_type,
        external_id,
        payload.message_id,
    )

    await sender.send(UpsertQAPairCommand(external_id=ExternalId(value=external_id)))
    logger.info("upsert_qa_pair_task: '%s' projected", external_id)


@inject(patch_module=True)
async def remove_qa_pair_task(
    payload: OutboxEventPayload[QAPairEventBody],
    sender: FromDishka[Sender],
) -> None:
    """Clears a removed pair from the search index."""
    external_id = payload.body.external_id.value
    logger.info(
        "remove_qa_pair_task: %s for '%s' (message %s)",
        payload.event_type,
        external_id,
        payload.message_id,
    )

    await sender.send(RemoveQAPairCommand(external_id=ExternalId(value=external_id)))
    logger.info("remove_qa_pair_task: '%s' cleared", external_id)


def setup_projection_tasks(broker: AsyncBroker) -> None:
    """Registers the projection tasks under the events that trigger them.

    Retries, unlike the indexing task: projection is idempotent, and a failure
    here is almost always the vector store being briefly unavailable rather than
    bad data. Giving up would leave the index permanently behind the catalog
    with nothing to notice it.
    """
    for event in (QAPairAdded, QAPairContentUpdated):
        broker.register_task(
            func=upsert_qa_pair_task,
            task_name=event.__name__,
            retry_on_error=True,
            max_retries=MAX_RETRIES,
            delay=RETRY_DELAY_SECONDS,
        )

    broker.register_task(
        func=remove_qa_pair_task,
        task_name=QAPairRemoved.__name__,
        retry_on_error=True,
        max_retries=MAX_RETRIES,
        delay=RETRY_DELAY_SECONDS,
    )
