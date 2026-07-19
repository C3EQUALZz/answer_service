"""Settling indexing runs whose worker never came back.

``RUNNING`` is committed in a transaction of its own so the status API can show
it, which is exactly what makes it a trap: a worker that dies during the sync
leaves the row there and nothing else will ever touch it. These tests pin the
two halves of the safeguard — that a genuinely abandoned run is failed, and that
a run which is merely slow is left alone.
"""

from datetime import UTC, datetime, timedelta

import pytest

from answer_service.application.commands.indexing.reap_stuck_tasks.command import (
    ReapStuckTasksCommand,
)
from answer_service.application.commands.indexing.reap_stuck_tasks.handler import (
    ABANDONED_FAILURE_CODE,
    ReapStuckTasksHandler,
)
from answer_service.domain.common.events_collection import EventsCollection
from answer_service.domain.indexing.entities.indexing_task import IndexingTask
from answer_service.domain.indexing.errors import InvalidTaskTransitionError
from answer_service.domain.indexing.factories.indexing_task_factory import (
    IndexingTaskFactory,
)
from answer_service.domain.indexing.value_objects.failure_info import FailureInfo
from answer_service.domain.indexing.value_objects.sync_stats import SyncStats
from answer_service.domain.indexing.value_objects.task_status import IndexingTaskStatus
from tests.unit.factories.domain_factories import make_source_reference
from tests.unit.stubs.gateways import InMemoryIndexingTaskGateway

STUCK_AFTER = timedelta(hours=1)

ABANDONED = FailureInfo(code=ABANDONED_FAILURE_CODE, message="stuck")


@pytest.fixture()
def handler(task_gateway: InMemoryIndexingTaskGateway) -> ReapStuckTasksHandler:
    return ReapStuckTasksHandler(task_gateway)


def make_task(
    factory: IndexingTaskFactory,
    *,
    started_ago: timedelta | None = None,
) -> IndexingTask:
    """A task in whatever lifecycle state the caller needs.

    ``started_at`` is rewritten rather than waited for, so a run that began two
    hours ago costs a test nothing.
    """
    task = factory.create(source=make_source_reference())
    if started_ago is not None:
        task.start()
        task.started_at = datetime.now(UTC) - started_ago
    return task


async def test_a_run_abandoned_by_its_worker_is_failed(
    handler: ReapStuckTasksHandler,
    task_gateway: InMemoryIndexingTaskGateway,
    indexing_task_factory: IndexingTaskFactory,
) -> None:
    task = make_task(indexing_task_factory, started_ago=timedelta(hours=2))
    await task_gateway.add(task)

    response = await handler.handle(ReapStuckTasksCommand(stuck_after=STUCK_AFTER))

    assert response.reaped == 1
    assert task.status is IndexingTaskStatus.FAILED
    assert task.failure is not None
    assert task.failure.code == ABANDONED_FAILURE_CODE
    assert task.finished_at is not None


async def test_a_run_that_is_merely_slow_is_left_alone(
    handler: ReapStuckTasksHandler,
    task_gateway: InMemoryIndexingTaskGateway,
    indexing_task_factory: IndexingTaskFactory,
) -> None:
    """Failing a task underneath a working sync is the way this goes wrong."""
    task = make_task(indexing_task_factory, started_ago=timedelta(minutes=5))
    await task_gateway.add(task)

    response = await handler.handle(ReapStuckTasksCommand(stuck_after=STUCK_AFTER))

    assert response.reaped == 0
    assert task.status is IndexingTaskStatus.RUNNING


async def test_a_queued_run_is_never_reaped(
    handler: ReapStuckTasksHandler,
    task_gateway: InMemoryIndexingTaskGateway,
    indexing_task_factory: IndexingTaskFactory,
) -> None:
    """It has not been picked up yet; it is still someone's to run."""
    task = make_task(indexing_task_factory)
    await task_gateway.add(task)

    response = await handler.handle(ReapStuckTasksCommand(stuck_after=STUCK_AFTER))

    assert response.reaped == 0
    assert task.status is IndexingTaskStatus.QUEUED


async def test_a_finished_run_is_never_reaped(
    handler: ReapStuckTasksHandler,
    task_gateway: InMemoryIndexingTaskGateway,
    indexing_task_factory: IndexingTaskFactory,
) -> None:
    task = make_task(indexing_task_factory, started_ago=timedelta(hours=2))
    task.complete(SyncStats.empty())
    await task_gateway.add(task)

    response = await handler.handle(ReapStuckTasksCommand(stuck_after=STUCK_AFTER))

    assert response.reaped == 0
    assert task.status is IndexingTaskStatus.SUCCEEDED


async def test_reaping_records_the_failure_as_an_event(
    handler: ReapStuckTasksHandler,
    task_gateway: InMemoryIndexingTaskGateway,
    indexing_task_factory: IndexingTaskFactory,
    events_collection: EventsCollection,
) -> None:
    """The lifecycle task consumes IndexingFailed, so it has to be raised."""
    task = make_task(indexing_task_factory, started_ago=timedelta(hours=2))
    await task_gateway.add(task)
    events_collection.pull_events()

    await handler.handle(ReapStuckTasksCommand(stuck_after=STUCK_AFTER))

    published = [type(event).__name__ for event in events_collection.pull_events()]
    assert published == ["IndexingFailed"]


async def test_the_batch_size_bounds_one_tick(
    handler: ReapStuckTasksHandler,
    task_gateway: InMemoryIndexingTaskGateway,
    indexing_task_factory: IndexingTaskFactory,
) -> None:
    """A backlog must not be settled in one unbounded transaction."""
    for _ in range(5):
        await task_gateway.add(
            make_task(indexing_task_factory, started_ago=timedelta(hours=2)),
        )

    response = await handler.handle(
        ReapStuckTasksCommand(stuck_after=STUCK_AFTER, batch_size=2),
    )

    assert response.reaped == 2


async def test_an_empty_sweep_touches_nothing(
    handler: ReapStuckTasksHandler,
    task_gateway: InMemoryIndexingTaskGateway,
) -> None:
    response = await handler.handle(ReapStuckTasksCommand(stuck_after=STUCK_AFTER))

    assert response.reaped == 0
    assert task_gateway.updated == []


def test_only_a_running_task_can_be_abandoned(
    indexing_task_factory: IndexingTaskFactory,
) -> None:
    """The transition is narrowed in the aggregate, not only in the query."""
    task = make_task(indexing_task_factory)

    with pytest.raises(InvalidTaskTransitionError):
        task.abandon(ABANDONED)
