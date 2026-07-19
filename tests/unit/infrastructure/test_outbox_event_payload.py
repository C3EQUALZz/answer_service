"""The envelope every relayed domain event travels in.

Getting a body model wrong is the kind of bug that only shows up in the worker:
the publisher forwards whatever the outbox stored, and the mismatch surfaces one
hop later as a validation error on a message nobody is watching.
"""

import json
from uuid import uuid4

import pytest
from pydantic import ValidationError

from answer_service.application.common.ports.task_manager import (
    IndexingTaskQueuedBody,
    OutboxEventPayload,
    QAPairEventBody,
    RawEventBody,
)


def test_a_task_id_is_read_from_the_bare_string_adaptix_writes() -> None:
    """``TaskId`` is a ``NewType`` over ``UUID``, so it is dumped unwrapped."""
    task_id = uuid4()

    body = IndexingTaskQueuedBody.model_validate({"task_id": str(task_id)})

    assert body.task_id == task_id


def test_an_external_id_is_read_through_the_value_object_it_is_dumped_as() -> None:
    """``ExternalId`` is a dataclass value object, so it lands as an object."""
    body = QAPairEventBody.model_validate({"external_id": {"value": "q-1"}})

    assert body.external_id.value == "q-1"


def test_a_body_ignores_the_fields_its_task_does_not_read() -> None:
    """Events carry identity and timestamps every consumer has no use for."""
    body = IndexingTaskQueuedBody.model_validate(
        {"task_id": str(uuid4()), "event_id": str(uuid4()), "event_date": "2026-01-01"},
    )

    assert body.task_id is not None


def test_a_body_missing_what_its_task_needs_is_rejected() -> None:
    with pytest.raises(ValidationError):
        IndexingTaskQueuedBody.model_validate({"unrelated": 1})


def test_the_publisher_forwards_fields_it_does_not_understand() -> None:
    """It reads the row without knowing which task will read the body."""
    task_id = uuid4()
    stored = json.dumps({"task_id": str(task_id), "extra": "kept"})

    envelope = OutboxEventPayload[RawEventBody](
        message_id=uuid4(),
        event_type="IndexingTaskQueued",
        body=RawEventBody.model_validate(json.loads(stored)),
    )
    delivered = OutboxEventPayload[IndexingTaskQueuedBody].model_validate(
        json.loads(envelope.model_dump_json()),
    )

    assert delivered.body.task_id == task_id


def test_the_message_id_identifies_the_delivery() -> None:
    """Two relays of one row carry one id, which is what deduplicates them."""
    message_id = uuid4()

    envelope = OutboxEventPayload[RawEventBody](
        message_id=message_id,
        event_type="QAPairAdded",
        body=RawEventBody.model_validate({"external_id": {"value": "q-1"}}),
    )

    assert envelope.message_id == message_id
