import pytest

from answer_service.domain.indexing.errors import InvalidTaskTransitionError
from answer_service.domain.indexing.value_objects.failure_info import FailureInfo
from answer_service.domain.indexing.value_objects.sync_stats import SyncStats
from answer_service.domain.indexing.value_objects.task_status import IndexingTaskStatus
from tests.unit.factories.domain_factories import make_queued_indexing_task
from tests.unit.support import emitted_event_names


def test_a_queued_task_records_its_arrival() -> None:
    task, collection = make_queued_indexing_task()

    assert task.status is IndexingTaskStatus.QUEUED
    assert task.started_at is None
    assert task.stats.total == 0
    assert emitted_event_names(collection) == ["IndexingTaskQueued"]


def test_starting_moves_to_running_and_stamps_the_time() -> None:
    task, collection = make_queued_indexing_task()
    emitted_event_names(collection)

    task.start()

    assert task.status is IndexingTaskStatus.RUNNING
    assert task.started_at is not None
    assert emitted_event_names(collection) == ["IndexingStarted"]


def test_completing_records_the_stats() -> None:
    task, _ = make_queued_indexing_task()
    task.start()
    stats = SyncStats(created=3, updated=1, deleted=0, skipped=7)

    task.complete(stats)

    assert task.status is IndexingTaskStatus.SUCCEEDED
    assert task.stats == stats
    assert task.finished_at is not None


def test_a_task_cannot_start_twice() -> None:
    """The worker's message is redelivered; the aggregate must hold the line."""
    task, _ = make_queued_indexing_task()
    task.start()

    with pytest.raises(InvalidTaskTransitionError):
        task.start()


def test_a_queued_task_cannot_be_completed() -> None:
    """Completing work that never started would report stats nobody produced."""
    task, _ = make_queued_indexing_task()

    with pytest.raises(InvalidTaskTransitionError):
        task.complete(SyncStats.empty())


def test_a_finished_task_cannot_be_completed_again() -> None:
    task, _ = make_queued_indexing_task()
    task.start()
    task.complete(SyncStats.empty())

    with pytest.raises(InvalidTaskTransitionError):
        task.complete(SyncStats.empty())


@pytest.mark.parametrize("started", (True, False))
def test_a_task_can_fail_from_any_non_terminal_state(*, started: bool) -> None:
    """A crash before the work began still has to be recorded."""
    task, _ = make_queued_indexing_task()
    if started:
        task.start()

    task.fail(FailureInfo(code="Boom", message="bad file"))

    assert task.status is IndexingTaskStatus.FAILED
    assert task.failure is not None
    assert task.finished_at is not None


@pytest.mark.parametrize("terminal_call", ("complete", "fail"))
def test_a_terminal_task_cannot_fail(terminal_call: str) -> None:
    task, _ = make_queued_indexing_task()
    task.start()
    if terminal_call == "complete":
        task.complete(SyncStats.empty())
    else:
        task.fail(FailureInfo(code="First", message="first failure"))

    with pytest.raises(InvalidTaskTransitionError):
        task.fail(FailureInfo(code="Second", message="late failure"))


def test_the_full_lifecycle_emits_its_events_in_order() -> None:
    task, collection = make_queued_indexing_task()
    task.start()
    task.complete(SyncStats.empty())

    assert emitted_event_names(collection) == [
        "IndexingTaskQueued",
        "IndexingStarted",
        "IndexingCompleted",
    ]
