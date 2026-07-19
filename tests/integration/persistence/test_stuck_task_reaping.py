"""Reaping abandoned indexing runs against a real PostgreSQL.

The unit tests cover the decision; this covers the query it rests on. The
filter is a timestamp comparison against a column written by a different
transaction, and `started_at` is stored by an imperative mapping — neither is
something a stub can get wrong on your behalf.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from dishka import AsyncContainer, Scope

from answer_service.application.commands.indexing.reap_stuck_tasks.command import (
    ReapStuckTasksCommand,
)
from answer_service.application.common.mediator.sender import Sender
from answer_service.application.common.ports.gateways import (
    IndexingTaskCommandGateway,
    IndexingTaskQueryGateway,
)
from answer_service.domain.indexing.entities.indexing_task import IndexingTask
from answer_service.domain.indexing.value_objects.source_reference import (
    SourceReference,
)
from answer_service.domain.indexing.value_objects.task_id import TaskId
from answer_service.domain.indexing.value_objects.task_status import IndexingTaskStatus
from tests.integration.arrange import TaskStorer
from tests.unit.factories.domain_factories import make_events_collection

pytestmark = [
    pytest.mark.asyncio(loop_scope="session"),
    pytest.mark.usefixtures("clean_tables"),
]

STUCK_AFTER = timedelta(hours=1)


def running_task(task_id: str, *, started_ago: timedelta) -> IndexingTask:
    """A task already in ``RUNNING``, started as long ago as the test needs."""
    task = IndexingTask.queue(
        task_id=TaskId(UUID(task_id)),
        source=SourceReference(value="uploads/faq.csv"),
        events_collection=make_events_collection(),
    )
    task.start()
    task.started_at = datetime.now(UTC) - started_ago
    return task


async def read_status(
    container: AsyncContainer,
    task_id: TaskId,
) -> IndexingTaskStatus:
    async with container(scope=Scope.REQUEST) as scope:
        gateway = await scope.get(IndexingTaskQueryGateway)
        view = await gateway.read_by_id(task_id)
        assert view is not None
        status: IndexingTaskStatus = view.status
        return status


async def test_an_abandoned_run_is_settled_as_failed(
    container: AsyncContainer,
    store_indexing_task: TaskStorer,
) -> None:
    task_id = await store_indexing_task(
        running_task(
            "aaaaaaaa-0000-0000-0000-000000000001",
            started_ago=timedelta(hours=2),
        ),
    )

    async with container(scope=Scope.REQUEST) as scope:
        sender = await scope.get(Sender)
        response = await sender.send(ReapStuckTasksCommand(stuck_after=STUCK_AFTER))

    assert response.reaped == 1
    assert await read_status(container, task_id) is IndexingTaskStatus.FAILED


async def test_a_recent_run_survives_the_sweep(
    container: AsyncContainer,
    store_indexing_task: TaskStorer,
) -> None:
    """The timestamp filter is the whole safeguard against reaping live work."""
    task_id = await store_indexing_task(
        running_task(
            "aaaaaaaa-0000-0000-0000-000000000002",
            started_ago=timedelta(minutes=1),
        ),
    )

    async with container(scope=Scope.REQUEST) as scope:
        sender = await scope.get(Sender)
        response = await sender.send(ReapStuckTasksCommand(stuck_after=STUCK_AFTER))

    assert response.reaped == 0
    assert await read_status(container, task_id) is IndexingTaskStatus.RUNNING


async def test_the_failure_reaches_the_outbox(
    container: AsyncContainer,
    store_indexing_task: TaskStorer,
) -> None:
    """Reaping runs through the pipelines, so IndexingFailed must be persisted."""
    await store_indexing_task(
        running_task(
            "aaaaaaaa-0000-0000-0000-000000000003",
            started_ago=timedelta(hours=2),
        ),
    )

    async with container(scope=Scope.REQUEST) as scope:
        sender = await scope.get(Sender)
        await sender.send(ReapStuckTasksCommand(stuck_after=STUCK_AFTER))

    async with container(scope=Scope.REQUEST) as scope:
        gateway = await scope.get(IndexingTaskCommandGateway)
        stuck = await gateway.read_stuck(
            started_before=datetime.now(UTC),
            limit=10,
        )

    assert stuck == []


async def test_a_second_sweep_finds_nothing_left(
    container: AsyncContainer,
    store_indexing_task: TaskStorer,
) -> None:
    """Reaping is not something a retried cron tick should redo."""
    await store_indexing_task(
        running_task(
            "aaaaaaaa-0000-0000-0000-000000000004",
            started_ago=timedelta(hours=2),
        ),
    )

    async with container(scope=Scope.REQUEST) as scope:
        sender = await scope.get(Sender)
        first = await sender.send(ReapStuckTasksCommand(stuck_after=STUCK_AFTER))

    async with container(scope=Scope.REQUEST) as scope:
        sender = await scope.get(Sender)
        second = await sender.send(ReapStuckTasksCommand(stuck_after=STUCK_AFTER))

    assert first.reaped == 1
    assert second.reaped == 0
