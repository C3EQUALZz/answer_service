"""Tests for the two lifecycle-fixation commands.

They live together because their contract is the same one: each runs in its own
transaction, and each must tolerate redelivery of the worker's message without
raising, since the state machine may already have moved past it.
"""

import pytest

from answer_service.application.commands.indexing.mark_indexing_failed.command import (
    MarkIndexingFailedCommand,
)
from answer_service.application.commands.indexing.mark_indexing_failed.handler import (
    MarkIndexingFailedHandler,
)
from answer_service.application.commands.indexing.mark_indexing_running.command import (
    MarkIndexingRunningCommand,
)
from answer_service.application.commands.indexing.mark_indexing_running.handler import (
    MarkIndexingRunningHandler,
)
from answer_service.application.error import IndexingTaskNotFoundError
from answer_service.domain.indexing.entities.indexing_task import IndexingTask
from answer_service.domain.indexing.value_objects.sync_stats import SyncStats
from answer_service.domain.indexing.value_objects.task_status import IndexingTaskStatus
from tests.unit.factories.domain_factories import make_task_id
from tests.unit.stubs.gateways import InMemoryIndexingTaskGateway


async def test_marks_a_queued_task_running(
    queued_task: IndexingTask,
    task_gateway: InMemoryIndexingTaskGateway,
) -> None:
    handler = MarkIndexingRunningHandler(task_gateway)

    await handler.handle(MarkIndexingRunningCommand(task_id=queued_task.id))

    assert queued_task.status is IndexingTaskStatus.RUNNING
    assert queued_task.started_at is not None
    assert task_gateway.updated == [queued_task.id]


async def test_marking_running_twice_is_a_no_op(
    queued_task: IndexingTask,
    task_gateway: InMemoryIndexingTaskGateway,
) -> None:
    """A redelivered message must not blow up on the state machine."""
    handler = MarkIndexingRunningHandler(task_gateway)
    command = MarkIndexingRunningCommand(task_id=queued_task.id)

    await handler.handle(command)
    started_at = queued_task.started_at
    await handler.handle(command)

    assert queued_task.status is IndexingTaskStatus.RUNNING
    assert queued_task.started_at == started_at
    assert task_gateway.updated == [queued_task.id]


async def test_marking_running_a_finished_task_does_not_restart_it(
    running_task: IndexingTask,
    task_gateway: InMemoryIndexingTaskGateway,
) -> None:
    running_task.complete(SyncStats.empty())
    handler = MarkIndexingRunningHandler(task_gateway)

    await handler.handle(MarkIndexingRunningCommand(task_id=running_task.id))

    assert running_task.status is IndexingTaskStatus.SUCCEEDED


async def test_records_the_failure_reason(
    running_task: IndexingTask,
    task_gateway: InMemoryIndexingTaskGateway,
) -> None:
    handler = MarkIndexingFailedHandler(task_gateway)

    await handler.handle(
        MarkIndexingFailedCommand(
            task_id=running_task.id,
            code="UnsupportedSourceFormatError",
            message="not a CSV",
        ),
    )

    assert running_task.status is IndexingTaskStatus.FAILED
    assert running_task.failure is not None
    assert running_task.failure.code == "UnsupportedSourceFormatError"
    assert task_gateway.updated == [running_task.id]


async def test_failing_an_already_finished_task_keeps_the_original_outcome(
    running_task: IndexingTask,
    task_gateway: InMemoryIndexingTaskGateway,
) -> None:
    """Retrying the compensation step must not overwrite a terminal state."""
    running_task.complete(SyncStats(created=3, updated=0, deleted=0, skipped=0))
    handler = MarkIndexingFailedHandler(task_gateway)

    await handler.handle(
        MarkIndexingFailedCommand(task_id=running_task.id, code="Boom", message="late"),
    )

    assert running_task.status is IndexingTaskStatus.SUCCEEDED
    assert running_task.failure is None
    assert task_gateway.updated == []


async def test_marking_running_raises_when_the_task_is_missing(
    task_gateway: InMemoryIndexingTaskGateway,
) -> None:
    handler = MarkIndexingRunningHandler(task_gateway)

    command = MarkIndexingRunningCommand(task_id=make_task_id())

    with pytest.raises(IndexingTaskNotFoundError):
        await handler.handle(command)


async def test_marking_failed_raises_when_the_task_is_missing(
    task_gateway: InMemoryIndexingTaskGateway,
) -> None:
    handler = MarkIndexingFailedHandler(task_gateway)

    command = MarkIndexingFailedCommand(
        task_id=make_task_id(),
        code="Boom",
        message="gone",
    )

    with pytest.raises(IndexingTaskNotFoundError):
        await handler.handle(command)
