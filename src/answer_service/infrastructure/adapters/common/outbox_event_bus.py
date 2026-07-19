import logging
from collections.abc import Iterable
from typing import Final, final, override

from answer_service.application.common.ports.outbox.event_bus import EventBus
from answer_service.application.common.ports.outbox.event_serializer import (
    EventSerializer,
)
from answer_service.application.common.ports.outbox.outbox_command_gateway import (
    OutboxCommandGateway,
)
from answer_service.domain.common.event import Event

logger: Final[logging.Logger] = logging.getLogger(__name__)


@final
class OutboxEventBus(EventBus):
    """EventBus backed by the Outbox pattern.

    For each domain event:
    1. Serializes the event and persists it to the ``outbox_messages`` table
       **within the current request transaction** (at-least-once delivery).

    The ``OutboxRelay`` is responsible for reading pending outbox messages
    and publishing them to RabbitMQ asynchronously.
    """

    def __init__(
        self,
        outbox_command_gateway: OutboxCommandGateway,
        event_serializer: EventSerializer,
    ) -> None:
        self._outbox_command_gateway: Final[OutboxCommandGateway] = outbox_command_gateway
        self._event_serializer: Final[EventSerializer] = event_serializer

    @override
    async def publish(self, events: Iterable[Event]) -> None:
        written = 0
        for event in events:
            message = self._event_serializer.serialize(event)
            await self._outbox_command_gateway.add(message)
            written += 1
            logger.debug(
                "outbox_bus: wrote %s as message %s",
                message.event_type,
                message.id,
            )

        log = logger.info if written else logger.debug
        log("outbox_bus: wrote %d event(s) to the outbox", written)
