import logging
from collections.abc import Iterable
from typing import Final

from taskiq import AsyncBroker

from answer_service.application.common.ports.task_manager import (
    EventBody,
    OutboxEventPayload,
)
from answer_service.domain.common.event import Event
from answer_service.domain.indexing.events import (
    IndexingCompleted,
    IndexingFailed,
    IndexingStarted,
)

logger: Final[logging.Logger] = logging.getLogger(__name__)

UNCONSUMED_EVENTS: Final[Iterable[type[Event]]] = (
    IndexingStarted,
    IndexingCompleted,
    IndexingFailed,
)


def record_lifecycle_event_task(payload: OutboxEventPayload[EventBody]) -> None:
    """Acknowledges an event nothing acts on yet.

    These three describe a task's progress, which the API already reads from the
    database — nobody needs them relayed. They reach the outbox anyway, and the
    publisher refuses to schedule an event with no registered task, so they need
    a registration even though there is nothing to do.

    Giving them a real task rather than a catch-all fallback is the point: an
    event that reaches here was listed below on purpose, and one that was
    forgotten fails loudly at publish time instead of vanishing.
    """
    logger.debug(
        "lifecycle: %s (message %s) has no projection",
        payload.event_type,
        payload.message_id,
    )


def setup_lifecycle_tasks(broker: AsyncBroker) -> None:
    for event in UNCONSUMED_EVENTS:
        broker.register_task(
            func=record_lifecycle_event_task,
            task_name=event.__name__,
        )
