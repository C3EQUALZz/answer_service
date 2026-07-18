import pytest

from answer_service.application.commands.indexing.run_indexing.command import (
    RunIndexingCommand,
)
from answer_service.application.error import IndexingTaskNotFoundError
from answer_service.domain.common.events_collection import EventsCollection
from answer_service.domain.indexing.entities.indexing_task import IndexingTask
from answer_service.domain.indexing.errors import DuplicateExternalIdError
from answer_service.domain.indexing.factories.qa_pair_factory import QAPairFactory
from answer_service.domain.indexing.value_objects.external_id import ExternalId
from answer_service.domain.indexing.value_objects.task_status import IndexingTaskStatus
from tests.unit.factories.domain_factories import (
    make_qa_content,
    make_qa_pair,
    make_source_row,
    make_task_id,
)
from tests.unit.factories.handler_factories import RunIndexingHandlerBuilder
from tests.unit.stubs.gateways import InMemoryQACatalog


async def test_creates_pairs_missing_from_the_catalog(
    running_task: IndexingTask,
    catalog: InMemoryQACatalog,
    run_indexing_handler: RunIndexingHandlerBuilder,
) -> None:
    handler = run_indexing_handler([make_source_row("q-1"), make_source_row("q-2")])

    await handler.handle(RunIndexingCommand(task_id=running_task.id))

    assert catalog.added == [ExternalId(value="q-1"), ExternalId(value="q-2")]
    assert running_task.status is IndexingTaskStatus.SUCCEEDED
    assert running_task.stats.created == 2
    assert running_task.stats.total == 2


async def test_rerunning_an_unchanged_file_changes_nothing(
    running_task: IndexingTask,
    catalog: InMemoryQACatalog,
    qa_pair_factory: QAPairFactory,
    run_indexing_handler: RunIndexingHandlerBuilder,
) -> None:
    """The whole point of fingerprint-based diffing: a no-op sync writes nothing."""
    row = make_source_row("q-1")
    await catalog.add(
        qa_pair_factory.create(
            external_id=ExternalId(value="q-1"),
            content=make_qa_content(),
            source_updated_at=row.updated_at,
        ),
    )
    catalog.added.clear()
    handler = run_indexing_handler([row])

    await handler.handle(RunIndexingCommand(task_id=running_task.id))

    assert catalog.added == []
    assert catalog.updated == []
    assert catalog.deleted == []
    assert running_task.stats.skipped == 1


async def test_updates_changed_pairs_and_deletes_the_ones_gone_from_the_source(
    running_task: IndexingTask,
    catalog: InMemoryQACatalog,
    qa_pair_factory: QAPairFactory,
    run_indexing_handler: RunIndexingHandlerBuilder,
) -> None:
    await catalog.add(
        qa_pair_factory.create(
            external_id=ExternalId(value="q-1"),
            content=make_qa_content(answer="Old answer."),
            source_updated_at=make_source_row("q-1").updated_at,
        ),
    )
    await catalog.add(
        qa_pair_factory.create(
            external_id=ExternalId(value="q-stale"),
            content=make_qa_content(),
            source_updated_at=make_source_row("q-stale").updated_at,
        ),
    )
    handler = run_indexing_handler([make_source_row("q-1", answer="New answer.")])

    await handler.handle(RunIndexingCommand(task_id=running_task.id))

    assert catalog.updated == [ExternalId(value="q-1")]
    assert catalog.deleted == [ExternalId(value="q-stale")]
    updated_pair = catalog.pairs[ExternalId(value="q-1")]
    assert updated_pair.content.answer.content == "New answer."
    assert running_task.stats.updated == 1
    assert running_task.stats.deleted == 1


async def test_a_duplicated_external_id_aborts_the_run(
    running_task: IndexingTask,
    catalog: InMemoryQACatalog,
    run_indexing_handler: RunIndexingHandlerBuilder,
) -> None:
    """The handler must propagate so the transaction pipeline rolls the work back."""
    handler = run_indexing_handler([make_source_row("q-1"), make_source_row("q-1")])

    with pytest.raises(DuplicateExternalIdError):
        await handler.handle(RunIndexingCommand(task_id=running_task.id))

    assert catalog.added == []
    assert running_task.status is IndexingTaskStatus.RUNNING


async def test_raises_when_the_task_is_missing(
    run_indexing_handler: RunIndexingHandlerBuilder,
) -> None:
    handler = run_indexing_handler()

    with pytest.raises(IndexingTaskNotFoundError):
        await handler.handle(RunIndexingCommand(task_id=make_task_id()))


async def test_removal_goes_through_the_aggregate(
    running_task: IndexingTask,
    catalog: InMemoryQACatalog,
    events_collection: EventsCollection,
    run_indexing_handler: RunIndexingHandlerBuilder,
) -> None:
    """A silent delete would leave the pair in the search index forever."""
    await catalog.add(make_qa_pair("q-gone", events_collection))
    handler = run_indexing_handler()

    await handler.handle(RunIndexingCommand(task_id=running_task.id))

    assert catalog.deleted == [ExternalId(value="q-gone")]
    emitted = [type(event).__name__ for event in events_collection.pull_events()]
    assert "QAPairRemoved" in emitted
