from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class OutboxMessage:
    """DTO representing a single outbox entry.

    ``payload`` is a JSON string containing the serialized domain event.
    ``processed_at`` is None while the message is still pending relay.
    """

    id: UUID
    event_type: str
    payload: str
    created_at: datetime
    processed_at: datetime | None = None
