"""The IndexingTask mapping against a real database, through its ports.

The aggregate is stored with two JSONB value objects and a ``StrEnum`` column.
None of that can be checked by compiling DDL: it either round-trips or it
silently returns something else.
"""

from uuid import uuid4

import pytest
from dishka import AsyncContainer, FromDishka, Scope

from answer_service.application.common.ports.gateways import (
    IndexingTaskCommandGateway,
    IndexingTaskQueryGateway,
)
from answer_service.application.common.ports.transaction_manager import (
    TransactionManager,
)
from answer_service.domain.indexing.value_objects.failure_info import FailureInfo
from answer_service.domain.indexing.value_objects.sync_stats import SyncStats
from answer_service.domain.indexing.value_objects.task_id import TaskId
from answer_service.domain.indexing.value_objects.task_status import IndexingTaskStatus
from tests.integration.arrange import TaskStorer
from tests.integration.inject import inject
from tests.unit.factories.domain_factories import make_queued_indexing_task

pytestmark = [
    pytest.mark.asyncio(loop_scope="session"),
    pytest.mark.usefixtures("clean_tables"),
]


@inject
async def test_a_queued_task_round_trips(
    store_indexing_task: TaskStorer,
    gateway: FromDishka[IndexingTaskCommandGateway],
) -> None:
    task, _ = make_queued_indexing_task()
    task_id = await store_indexing_task(task)

    loaded = await gateway.read_by_id(task_id)

    assert loaded is not None
    assert loaded.id == task_id
    assert loaded.source == task.source
    assert loaded.status is IndexingTaskStatus.QUEUED
    assert loaded.started_at is None
    assert loaded.failure is None


@inject
async def test_the_status_comes_back_as_an_enum(
    store_indexing_task: TaskStorer,
    gateway: FromDishka[IndexingTaskCommandGateway],
) -> None:
    """``status.is_terminal`` is called on loaded aggregates; a str has no such thing."""
    task, _ = make_queued_indexing_task()
    task.start()
    task.complete(SyncStats.empty())
    task_id = await store_indexing_task(task)

    loaded = await gateway.read_by_id(task_id)

    assert loaded is not None
    assert loaded.status is IndexingTaskStatus.SUCCEEDED
    assert loaded.status.is_terminal


@inject
async def test_the_stats_survive_the_round_trip(
    store_indexing_task: TaskStorer,
    gateway: FromDishka[IndexingTaskCommandGateway],
) -> None:
    task, _ = make_queued_indexing_task()
    task.start()
    task.complete(SyncStats(created=3, updated=2, deleted=1, skipped=7))
    task_id = await store_indexing_task(task)

    loaded = await gateway.read_by_id(task_id)

    assert loaded is not None
    assert loaded.stats == SyncStats(created=3, updated=2, deleted=1, skipped=7)
    assert loaded.stats.total == 13


@inject
async def test_a_failure_survives_the_round_trip(
    store_indexing_task: TaskStorer,
    gateway: FromDishka[IndexingTaskCommandGateway],
) -> None:
    task, _ = make_queued_indexing_task()
    task.start()
    task.fail(FailureInfo(code="UnsupportedSourceFormatError", message="not a csv"))
    task_id = await store_indexing_task(task)

    loaded = await gateway.read_by_id(task_id)

    assert loaded is not None
    assert loaded.failure == FailureInfo(
        code="UnsupportedSourceFormatError",
        message="not a csv",
    )


async def test_a_loaded_task_can_continue_its_lifecycle(
    store_indexing_task: TaskStorer,
    container: AsyncContainer,
) -> None:
    """The worker loads a task and moves it on; the state machine must still work."""
    task, _ = make_queued_indexing_task()
    task_id = await store_indexing_task(task)

    async with container(scope=Scope.REQUEST) as worker_scope:
        gateway = await worker_scope.get(IndexingTaskCommandGateway)
        loaded = await gateway.read_by_id(task_id)
        assert loaded is not None
        loaded.start()
        loaded.complete(SyncStats(created=1, updated=0, deleted=0, skipped=0))
        await (await worker_scope.get(TransactionManager)).commit()

    async with container(scope=Scope.REQUEST) as reader_scope:
        reloaded = await (await reader_scope.get(IndexingTaskCommandGateway)).read_by_id(
            task_id
        )

    assert reloaded is not None
    assert reloaded.status is IndexingTaskStatus.SUCCEEDED
    assert reloaded.started_at is not None
    assert reloaded.finished_at is not None


@inject
async def test_an_unknown_task_is_absent_not_an_error(
    gateway: FromDishka[IndexingTaskCommandGateway],
) -> None:
    assert await gateway.read_by_id(TaskId(uuid4())) is None


@inject
async def test_the_status_view_reads_the_same_row(
    store_indexing_task: TaskStorer,
    query_gateway: FromDishka[IndexingTaskQueryGateway],
) -> None:
    """The read model and the aggregate must not disagree about the same task."""
    task, _ = make_queued_indexing_task()
    task.start()
    task.complete(SyncStats(created=2, updated=1, deleted=0, skipped=5))
    task_id = await store_indexing_task(task)

    view = await query_gateway.read_by_id(task_id)

    assert view is not None
    assert view.task_id == task_id
    assert view.status is IndexingTaskStatus.SUCCEEDED
    assert view.is_finished
    assert (view.created, view.updated, view.deleted, view.skipped) == (2, 1, 0, 5)
    assert view.failure_code is None


@inject
async def test_the_status_view_reports_a_failure(
    store_indexing_task: TaskStorer,
    query_gateway: FromDishka[IndexingTaskQueryGateway],
) -> None:
    task, _ = make_queued_indexing_task()
    task.start()
    task.fail(FailureInfo(code="Boom", message="bad file"))
    task_id = await store_indexing_task(task)

    view = await query_gateway.read_by_id(task_id)

    assert view is not None
    assert view.failure_code == "Boom"
    assert view.failure_message == "bad file"
    assert view.is_finished


@inject
async def test_an_unknown_task_has_no_status_view(
    query_gateway: FromDishka[IndexingTaskQueryGateway],
) -> None:
    assert await query_gateway.read_by_id(TaskId(uuid4())) is None
