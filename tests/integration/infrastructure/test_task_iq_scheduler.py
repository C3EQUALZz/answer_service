import asyncio
from uuid import uuid4

import pytest
from taskiq import AsyncBroker, InMemoryBroker

from answer_service.application.common.ports.task_manager import (
    ProjectEventPayload,
    RunIndexingPayload,
)
from answer_service.application.common.ports.task_manager.task_keys import (
    INDEXING_TASK_KEY,
    OUTBOX_TASK_KEY,
)
from answer_service.infrastructure.adapters.messaging.task_scheduler_outbox_publisher import (  # ruff:ignore[line-too-long]
    TaskSchedulerOutboxPublisher,
)
from answer_service.infrastructure.errors import UnregisteredTaskError
from answer_service.infrastructure.task_manager.task_iq_task_scheduler import (
    TaskIQTaskScheduler,
)
from tests.unit.factories.domain_factories import make_task_id
from tests.unit.factories.outbox_factories import make_outbox_message


def register_projection_task(
    broker: AsyncBroker,
    received: list[ProjectEventPayload],
) -> None:
    async def task(payload: ProjectEventPayload) -> None:  # ruff:ignore[unused-async]
        received.append(payload)

    broker.register_task(func=task, task_name=str(OUTBOX_TASK_KEY))


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
    task_id = scheduler.make_task_id(INDEXING_TASK_KEY, "abc")

    assert task_id == "indexing:abc"
    assert task_id.split(":")[0] == str(INDEXING_TASK_KEY)


async def test_scheduling_an_unregistered_task_fails_loudly(
    scheduler: TaskIQTaskScheduler,
) -> None:
    """Silently dropping the task would leave an upload queued forever."""
    with pytest.raises(UnregisteredTaskError, match="indexing"):
        await scheduler.schedule(
            scheduler.make_task_id(INDEXING_TASK_KEY, make_task_id()),
            RunIndexingPayload(task_id=make_task_id()),
        )


async def test_the_outbox_publisher_lands_on_the_projection_task(
    in_memory_broker: InMemoryBroker,
    scheduler: TaskIQTaskScheduler,
) -> None:
    """The publisher and the task registration must agree on the name."""
    received: list[ProjectEventPayload] = []
    register_projection_task(in_memory_broker, received)
    message = make_outbox_message("QAPairAdded")

    await TaskSchedulerOutboxPublisher(scheduler).publish(message)
    await drain(in_memory_broker)

    assert len(received) == 1
    assert received[0].message_id == message.id
    assert received[0].event_type == "QAPairAdded"


def test_redelivering_a_message_reuses_its_task_id(
    scheduler: TaskIQTaskScheduler,
) -> None:
    """Stability across retries is what an inbox check keys off."""
    message = make_outbox_message()

    first = scheduler.make_task_id(OUTBOX_TASK_KEY, message.id)
    second = scheduler.make_task_id(OUTBOX_TASK_KEY, message.id)

    assert first == second


def test_two_messages_get_different_task_ids(
    scheduler: TaskIQTaskScheduler,
) -> None:
    first = scheduler.make_task_id(OUTBOX_TASK_KEY, uuid4())
    second = scheduler.make_task_id(OUTBOX_TASK_KEY, uuid4())

    assert first != second


async def test_unknown_task_info_is_reported_as_missing(
    scheduler: TaskIQTaskScheduler,
) -> None:
    info = await scheduler.read_task_info(
        scheduler.make_task_id(INDEXING_TASK_KEY, uuid4()),
    )

    assert info is None
