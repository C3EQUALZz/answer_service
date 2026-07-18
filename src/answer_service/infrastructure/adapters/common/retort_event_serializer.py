import json
from datetime import UTC, datetime
from typing import Final, final, override
from uuid import UUID, uuid4

from adaptix import Retort, dumper

from answer_service.application.common.ports.outbox import (
    EventSerializer,
    OutboxMessage,
)
from answer_service.domain.common.event import Event
from answer_service.domain.common.event_id import EventId

_retort: Final[Retort] = Retort(
    recipe=[
        dumper(UUID, str),
        dumper(datetime, datetime.isoformat),
    ],
)


@final
class RetortEventSerializer(EventSerializer):
    """Renders domain events as JSON outbox rows via adaptix.

    Stamps the event with its identity and timestamp first: both setters are
    write-once, so re-serializing an already-stamped event keeps the original
    values and the payload stays byte-identical.
    """

    @override
    def serialize(self, event: Event) -> OutboxMessage:
        event.set_event_id(EventId(uuid4()))
        event.set_event_date(datetime.now(UTC))

        return OutboxMessage(
            id=uuid4(),
            event_type=event.event_type,
            payload=json.dumps(_retort.dump(event)),
            created_at=datetime.now(UTC),
        )
