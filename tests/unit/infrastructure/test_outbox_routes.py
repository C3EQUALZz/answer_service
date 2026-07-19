"""Routing of outbox messages to the task that reacts to them.

The table decides which background task an event becomes. Getting it wrong is
silent: an event routed to the projector is ignored rather than rejected, so a
misroute looks exactly like nothing happening.
"""

import json
from uuid import uuid4

import pytest

from answer_service.application.common.ports.task_manager import (
    ProjectEventPayload,
    RunIndexingPayload,
)
from answer_service.application.error import MalformedEventPayloadError
from answer_service.infrastructure.adapters.messaging.outbox_routes import route_for
from tests.unit.factories.outbox_factories import make_outbox_message


def test_a_queued_indexing_task_becomes_an_indexing_run() -> None:
    task_id = uuid4()
    message = make_outbox_message(
        event_type="IndexingTaskQueued",
        payload=json.dumps({"task_id": {"value": str(task_id)}}),
    )

    route = route_for(message.event_type)

    assert route.task_key == "indexing"
    assert route.build_payload(message) == RunIndexingPayload(task_id=task_id)


def test_the_indexing_task_id_identifies_the_run_rather_than_the_message() -> None:
    """Two relays of one message must land on the same task id, not two."""
    task_id = uuid4()
    payload = json.dumps({"task_id": {"value": str(task_id)}})
    first = make_outbox_message(event_type="IndexingTaskQueued", payload=payload)
    second = make_outbox_message(event_type="IndexingTaskQueued", payload=payload)

    route = route_for("IndexingTaskQueued")

    assert first.id != second.id
    assert route.subject_of(first) == route.subject_of(second) == task_id


def test_a_catalog_change_goes_to_the_projector() -> None:
    message = make_outbox_message(event_type="QAPairAdded")

    route = route_for(message.event_type)

    assert route.task_key == "outbox"
    assert route.build_payload(message) == ProjectEventPayload(
        message_id=message.id,
        event_type=message.event_type,
        payload=message.payload,
    )


def test_an_unrouted_event_falls_through_to_the_projector() -> None:
    """Adding a domain event must not require touching this table."""
    message = make_outbox_message(event_type="SomethingNobodyMappedYet")

    route = route_for(message.event_type)

    assert route.task_key == "outbox"
    assert route.subject_of(message) == message.id


def test_a_queued_event_without_a_task_id_is_rejected() -> None:
    message = make_outbox_message(
        event_type="IndexingTaskQueued",
        payload=json.dumps({"unrelated": 1}),
    )

    route = route_for(message.event_type)

    with pytest.raises(MalformedEventPayloadError):
        route.build_payload(message)
