"""Builders for the outbox DTOs the relay works over."""

from datetime import UTC, datetime
from uuid import uuid4

from answer_service.application.common.ports.outbox import OutboxMessage


def make_outbox_message(event_type: str = "QAPairAdded") -> OutboxMessage:
    return OutboxMessage(
        id=uuid4(),
        event_type=event_type,
        payload="{}",
        created_at=datetime.now(UTC),
    )
