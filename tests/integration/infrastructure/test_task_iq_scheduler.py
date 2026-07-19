import asyncio
import json
from uuid import uuid4

import pytest
from taskiq import AsyncBroker, InMemoryBroker

from answer_service.application.common.ports.task_manager import (
    IndexingTaskQueuedBody,
    OutboxEventPayload,
    QAPairEventBody,
)
from answer_service.application.common.ports.task_manager.task_id import TaskKey
from answer_service.infrastructure.adapters.messaging import (
    TaskSchedulerOutboxPublisher,
)
from answer_service.infrastructure.errors import UnregisteredTaskError
from answer_service.infrastructure.task_manager.task_iq_task_scheduler import (
    TaskIQTaskScheduler,
)
from tests.unit.factories.domain_factories import make_task_id
from tests.unit.factories.outbox_factories import make_event_payload, make_outbox_message


def register_projection_task(
    broker: AsyncBroker,
    received: list[OutboxEventPayload[QAPairEventBody]],
) -> None:
    async def task(  # ruff:ignore[unused-async]
        payload: OutboxEventPayload[QAPairEventBody],
    ) -> None:
        received.append(payload)

    broker.register_task(func=task, task_name="QAPairAdded")


def register_indexing_task(
    broker: AsyncBroker,
    received: list[OutboxEventPayload[IndexingTaskQueuedBody]],
) -> None:
    async def task(  # ruff:ignore[unused-async]
        payload: OutboxEventPayload[IndexingTaskQueuedBody],
    ) -> None:
        received.append(payload)

    broker.register_task(func=task, task_name="IndexingTaskQueued")


async def drain(broker: InMemoryBroker) -> None:
    """Lets the in-memory broker run what was kicked.

    ``schedule`` is fire-and-forget by design — it hands the task over and
    returns without a handle — so the test yields the loop instead of awaiting
    a result the production port never exposes.
    """
    del broker
    await asyncio.sleep(0)


def test_a_task_id_is_the_key_and_the_value(scheduler: TaskIQTaskScheduler) -> None:
    """The key half is what the scheduler resolves the registered task by."""
    task_id = scheduler.make_task_id(TaskKey("IndexingTaskQueued"), "abc")

    assert task_id == "IndexingTaskQueued:abc"
    assert task_id.split(":")[0] == "IndexingTaskQueued"


async def test_publishing_an_event_with_no_task_fails_loudly(
    scheduler: TaskIQTaskScheduler,
) -> None:
    """A dropped event would leave the index or an upload silently behind."""
    message = make_outbox_message(event_type="NobodyRegisteredThis")

    publisher = TaskSchedulerOutboxPublisher(scheduler)

    with pytest.raises(UnregisteredTaskError, match="NobodyRegisteredThis"):
        await publisher.publish(message)


async def test_the_publisher_lands_on_the_task_named_after_the_event(
    in_memory_broker: InMemoryBroker,
    scheduler: TaskIQTaskScheduler,
) -> None:
    """The publisher and the task registration must agree on the name."""
    received: list[OutboxEventPayload[QAPairEventBody]] = []
    register_projection_task(in_memory_broker, received)
    message = make_outbox_message("QAPairAdded", make_event_payload("q-1"))

    await TaskSchedulerOutboxPublisher(scheduler).publish(message)
    await drain(in_memory_broker)

    assert len(received) == 1
    assert received[0].message_id == message.id
    assert received[0].event_type == "QAPairAdded"
    assert received[0].body.external_id.value == "q-1"


async def test_the_body_arrives_parsed_into_the_type_the_task_asked_for(
    in_memory_broker: InMemoryBroker,
    scheduler: TaskIQTaskScheduler,
) -> None:
    """The publisher forwards raw JSON; taskiq validates it on the way in."""
    received: list[OutboxEventPayload[IndexingTaskQueuedBody]] = []
    register_indexing_task(in_memory_broker, received)
    task_id = make_task_id()
    message = make_outbox_message(
        "IndexingTaskQueued",
        json.dumps({"task_id": str(task_id), "event_id": str(uuid4())}),
    )

    await TaskSchedulerOutboxPublisher(scheduler).publish(message)
    await drain(in_memory_broker)

    assert received[0].body.task_id == task_id


def test_redelivering_a_message_reuses_its_task_id(
    scheduler: TaskIQTaskScheduler,
) -> None:
    """Stability across retries is what an inbox check keys off."""
    message = make_outbox_message("QAPairAdded", make_event_payload("q-1"))

    first = scheduler.make_task_id(TaskKey(message.event_type), message.id)
    second = scheduler.make_task_id(TaskKey(message.event_type), message.id)

    assert first == second


def test_two_messages_get_different_task_ids(
    scheduler: TaskIQTaskScheduler,
) -> None:
    first = scheduler.make_task_id(TaskKey("QAPairAdded"), uuid4())
    second = scheduler.make_task_id(TaskKey("QAPairAdded"), uuid4())

    assert first != second


async def test_unknown_task_info_is_reported_as_missing(
    scheduler: TaskIQTaskScheduler,
) -> None:
    info = await scheduler.read_task_info(
        scheduler.make_task_id(TaskKey("IndexingTaskQueued"), uuid4()),
    )

    assert info is None
