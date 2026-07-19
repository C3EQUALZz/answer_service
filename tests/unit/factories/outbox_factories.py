"""Builders for the outbox DTOs the relay works over."""

import json
from datetime import UTC, datetime
from uuid import uuid4

from answer_service.application.common.ports.outbox import OutboxMessage


def make_outbox_message(
    event_type: str = "QAPairAdded",
    payload: str = "{}",
) -> OutboxMessage:
    return OutboxMessage(
        id=uuid4(),
        event_type=event_type,
        payload=payload,
        created_at=datetime.now(UTC),
    )


def make_event_payload(external_id: str) -> str:
    """Serialized shape of a QA pair event, as the outbox stores it.

    ``external_id`` is nested because the value object is dumped as an object,
    not a bare string — the projector has to reach through that.
    """
    return json.dumps(
        {
            "event_id": str(uuid4()),
            "event_date": datetime.now(UTC).isoformat(),
            "external_id": {"value": external_id},
        },
    )
