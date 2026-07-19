"""Handing an outbox row to the task queue.

The publisher is the only thing standing between a committed domain event and
the task that reacts to it, and it does so without knowing which task that is.
"""

import json
from uuid import uuid4

from answer_service.application.common.ports.task_manager import (
    IndexingTaskQueuedBody,
    OutboxEventPayload,
)
from answer_service.infrastructure.adapters.messaging import (
    TaskSchedulerOutboxPublisher,
)
from tests.unit.factories.outbox_factories import make_outbox_message
from tests.unit.stubs.infrastructure import RecordingTaskScheduler


async def test_a_message_is_scheduled_under_the_name_of_its_event() -> None:
    """Task names are event names; that is what replaces a routing table."""
    scheduler = RecordingTaskScheduler()
    message = make_outbox_message(
        event_type="IndexingTaskQueued",
        payload=json.dumps({"task_id": str(uuid4())}),
    )

    await TaskSchedulerOutboxPublisher(scheduler).publish(message)

    task_id, _ = scheduler.scheduled[0]
    assert task_id.split(":")[0] == "IndexingTaskQueued"


async def test_two_relays_of_one_row_land_on_one_task_id() -> None:
    """Redelivery must not start the work twice."""
    scheduler = RecordingTaskScheduler()
    message = make_outbox_message(
        event_type="IndexingTaskQueued",
        payload=json.dumps({"task_id": str(uuid4())}),
    )
    publisher = TaskSchedulerOutboxPublisher(scheduler)

    await publisher.publish(message)
    await publisher.publish(message)

    first, second = (task_id for task_id, _ in scheduler.scheduled)
    assert first == second


async def test_the_stored_body_reaches_the_task_that_parses_it() -> None:
    scheduler = RecordingTaskScheduler()
    task_id = uuid4()
    message = make_outbox_message(
        event_type="IndexingTaskQueued",
        payload=json.dumps({"task_id": str(task_id), "event_id": str(uuid4())}),
    )

    await TaskSchedulerOutboxPublisher(scheduler).publish(message)

    _, payload = scheduler.scheduled[0]
    delivered = OutboxEventPayload[IndexingTaskQueuedBody].model_validate(
        json.loads(payload.model_dump_json()),
    )
    assert delivered.body.task_id == task_id
    assert delivered.event_type == "IndexingTaskQueued"
