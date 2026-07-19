"""End-to-end tests of a use case running through the pipeline stack.

The pipelines nest as ``TransactionPipeline -> EventsPipeline -> handler``, which
encodes two guarantees no single-handler test can show:

* events are drained and handed to the bus *before* the commit, so the outbox
  rows land in the same transaction as the state change they describe;
* a handler that raises produces a rollback and publishes nothing.

The stubs share a :class:`CallJournal`, so these tests assert the ordering
between the layers rather than just their individual effects.
"""

import pytest

from answer_service.application.commands.indexing.run_indexing.command import (
    RunIndexingCommand,
)
from answer_service.domain.common.events_collection import EventsCollection
from answer_service.domain.indexing.entities.indexing_task import IndexingTask
from answer_service.domain.indexing.errors import DuplicateExternalIdError
from answer_service.domain.indexing.value_objects.task_status import IndexingTaskStatus
from tests.unit.application.conftest import PipelineRunner
from tests.unit.factories.domain_factories import make_source_row
from tests.unit.factories.handler_factories import RunIndexingHandlerBuilder
from tests.unit.stubs.infrastructure import CallJournal, RecordingEventBus


async def test_events_are_published_before_the_commit(
    running_task: IndexingTask,
    run_indexing_handler: RunIndexingHandlerBuilder,
    pipeline_runner: PipelineRunner,
    event_bus: RecordingEventBus,
    journal: CallJournal,
) -> None:
    handler = run_indexing_handler([make_source_row("q-1")])

    await pipeline_runner(RunIndexingCommand(task_id=running_task.id), handler)

    assert journal.entries == ["publish", "commit"]
    assert running_task.status is IndexingTaskStatus.SUCCEEDED

    published = [type(event).__name__ for event in event_bus.published]
    assert "QAPairAdded" in published
    assert "IndexingCompleted" in published


async def test_the_collection_is_drained_so_events_are_published_once(
    running_task: IndexingTask,
    run_indexing_handler: RunIndexingHandlerBuilder,
    pipeline_runner: PipelineRunner,
    events_collection: EventsCollection,
    event_bus: RecordingEventBus,
) -> None:
    handler = run_indexing_handler([make_source_row("q-1")])

    await pipeline_runner(RunIndexingCommand(task_id=running_task.id), handler)

    assert event_bus.published != []
    assert list(events_collection.pull_events()) == []


async def test_a_failing_handler_rolls_back_and_publishes_nothing(
    running_task: IndexingTask,
    run_indexing_handler: RunIndexingHandlerBuilder,
    pipeline_runner: PipelineRunner,
    event_bus: RecordingEventBus,
    journal: CallJournal,
) -> None:
    """The events of a rolled-back run must never reach the bus."""
    handler = run_indexing_handler([make_source_row("q-1"), make_source_row("q-1")])

    command = RunIndexingCommand(task_id=running_task.id)

    with pytest.raises(DuplicateExternalIdError):
        await pipeline_runner(command, handler)

    assert journal.entries == ["rollback"]
    assert event_bus.published == []
