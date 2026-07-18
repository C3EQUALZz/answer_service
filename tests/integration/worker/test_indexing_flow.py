"""The background indexing pipeline, end to end.

The worker's job is a sequence of commands, each in its own transaction:

    mark_indexing_running → run_indexing → relay_outbox → project_event

Nothing here is stubbed below the ports. The file is read by polars, the catalog
lands in Postgres, the events go through the real outbox, and the projection
reaches an in-process Qdrant — so a pair uploaded over HTTP ends up findable by
the dense retriever.

Commands are dispatched through ``Sender`` rather than through the broker: the
mediator, the transaction pipeline and the events pipeline are exactly what this
is testing, and the broker only decides *when* a command runs.
"""

from uuid import UUID

import pytest
from dishka import FromDishka

from answer_service.application.commands.indexing.mark_indexing_running.command import (
    MarkIndexingRunningCommand,
)
from answer_service.application.commands.indexing.run_indexing.command import (
    RunIndexingCommand,
)
from answer_service.application.commands.outbox.relay_outbox.command import (
    RelayOutboxCommand,
)
from answer_service.application.commands.search.project_event.command import (
    ProjectEventCommand,
)
from answer_service.application.common.ports.gateways import (
    IndexingTaskQueryGateway,
    QACatalogQueryGateway,
)
from answer_service.application.common.ports.outbox import OutboxCommandGateway
from answer_service.application.common.ports.search import DenseRetriever
from answer_service.domain.indexing.value_objects.external_id import ExternalId
from answer_service.domain.indexing.value_objects.task_id import TaskId
from answer_service.domain.indexing.value_objects.task_status import IndexingTaskStatus
from answer_service.domain.search.value_objects.search_criteria import SearchCriteria
from answer_service.domain.search.value_objects.search_query import SearchQuery
from answer_service.domain.search.value_objects.top_k import TopK
from tests.integration.arrange import CommandSender, SourceFileUploader
from tests.integration.brokers import RecordingBroker
from tests.integration.inject import inject
from tests.unit.factories.source_file_factories import make_csv_bytes

pytestmark = [
    pytest.mark.asyncio(loop_scope="session"),
    pytest.mark.usefixtures("clean_tables"),
]


async def upload_and_run(
    upload_source_file: SourceFileUploader,
    send_command: CommandSender,
    content: bytes,
) -> TaskId:
    """Walks an upload through the two worker steps that do the sync."""
    response = await upload_source_file(content)
    task_id = TaskId(UUID(response.json()["task_id"]))

    await send_command(MarkIndexingRunningCommand(task_id=task_id))
    await send_command(RunIndexingCommand(task_id=task_id))
    return task_id


@inject
async def test_the_sync_populates_the_catalog(
    upload_source_file: SourceFileUploader,
    send_command: CommandSender,
    catalog: FromDishka[QACatalogQueryGateway],
) -> None:
    task_id = await upload_and_run(
        upload_source_file, send_command, make_csv_bytes(rows=3)
    )

    manifest = await catalog.read_fingerprints()

    assert set(manifest) == {ExternalId(value=f"q-{index}") for index in range(3)}
    assert task_id


@inject
async def test_the_task_ends_succeeded_with_its_counters(
    upload_source_file: SourceFileUploader,
    send_command: CommandSender,
    tasks: FromDishka[IndexingTaskQueryGateway],
) -> None:
    task_id = await upload_and_run(
        upload_source_file, send_command, make_csv_bytes(rows=2)
    )

    view = await tasks.read_by_id(task_id)

    assert view is not None
    assert view.status is IndexingTaskStatus.SUCCEEDED
    assert view.is_finished
    assert (view.created, view.updated, view.deleted, view.skipped) == (2, 0, 0, 0)
    assert view.finished_at is not None


@inject
async def test_the_status_is_visible_while_the_sync_runs(
    upload_source_file: SourceFileUploader,
    send_command: CommandSender,
    tasks: FromDishka[IndexingTaskQueryGateway],
) -> None:
    """``mark_indexing_running`` commits on its own so polling shows progress."""
    response = await upload_source_file(make_csv_bytes())
    task_id = TaskId(UUID(response.json()["task_id"]))

    await send_command(MarkIndexingRunningCommand(task_id=task_id))

    view = await tasks.read_by_id(task_id)
    assert view is not None
    assert view.status is IndexingTaskStatus.RUNNING
    assert not view.is_finished


@inject
async def test_rerunning_an_unchanged_file_skips_everything(
    upload_source_file: SourceFileUploader,
    send_command: CommandSender,
    tasks: FromDishka[IndexingTaskQueryGateway],
) -> None:
    """Fingerprint diffing is what makes a repeated upload nearly free."""
    content = make_csv_bytes(rows=3)
    await upload_and_run(upload_source_file, send_command, content)

    second_task_id = await upload_and_run(upload_source_file, send_command, content)

    view = await tasks.read_by_id(second_task_id)
    assert view is not None
    assert (view.created, view.updated, view.deleted, view.skipped) == (0, 0, 0, 3)


@inject
async def test_a_pair_missing_from_the_second_file_is_deleted(
    upload_source_file: SourceFileUploader,
    send_command: CommandSender,
    catalog: FromDishka[QACatalogQueryGateway],
    tasks: FromDishka[IndexingTaskQueryGateway],
) -> None:
    """The file is the source of truth: deletion is the set difference."""
    await upload_and_run(upload_source_file, send_command, make_csv_bytes(rows=3))

    task_id = await upload_and_run(
        upload_source_file, send_command, make_csv_bytes(rows=1)
    )

    manifest = await catalog.read_fingerprints()
    view = await tasks.read_by_id(task_id)
    assert set(manifest) == {ExternalId(value="q-0")}
    assert view is not None
    assert view.deleted == 2


@inject
async def test_the_sync_writes_its_events_to_the_outbox(
    upload_source_file: SourceFileUploader,
    send_command: CommandSender,
    outbox: FromDishka[OutboxCommandGateway],
) -> None:
    """The events must land in the same transaction as the catalog rows."""
    await upload_and_run(upload_source_file, send_command, make_csv_bytes(rows=2))

    pending = await outbox.read_pending(limit=50)

    event_types = [message.event_type for message in pending]
    assert event_types.count("QAPairAdded") == 2
    assert "IndexingCompleted" in event_types


async def test_the_relay_hands_every_event_to_the_projector(
    upload_source_file: SourceFileUploader,
    send_command: CommandSender,
    broker: RecordingBroker,
) -> None:
    await upload_and_run(upload_source_file, send_command, make_csv_bytes(rows=2))
    broker.forget_kicked()

    response = await send_command(RelayOutboxCommand())

    assert response.published == response.total
    assert response.total > 0
    assert set(broker.kicked_task_names) == {"outbox"}


async def test_a_relayed_message_is_not_relayed_again(
    upload_source_file: SourceFileUploader,
    send_command: CommandSender,
) -> None:
    """At-least-once delivery must not become at-least-twice on every tick."""
    await upload_and_run(upload_source_file, send_command, make_csv_bytes(rows=2))

    first = await send_command(RelayOutboxCommand())
    second = await send_command(RelayOutboxCommand())

    assert first.total > 0
    assert second.total == 0


@inject
async def test_a_projected_pair_becomes_findable(
    upload_source_file: SourceFileUploader,
    send_command: CommandSender,
    retriever: FromDishka[DenseRetriever],
) -> None:
    """The end of the road: uploaded, synced, relayed, projected, searchable."""
    await upload_and_run(upload_source_file, send_command, make_csv_bytes(rows=2))

    await send_command(
        ProjectEventCommand(
            message_id=UUID(int=0),
            event_type="QAPairAdded",
            payload='{"external_id": {"value": "q-0"}}',
        ),
    )

    found = await retriever.retrieve(
        SearchCriteria(query=SearchQuery(content="Question 0?"), top_k=TopK(value=5)),
    )

    assert [candidate.external_id for candidate in found] == [ExternalId(value="q-0")]


@inject
async def test_projecting_the_same_event_twice_keeps_one_entry(
    upload_source_file: SourceFileUploader,
    send_command: CommandSender,
    retriever: FromDishka[DenseRetriever],
) -> None:
    """Delivery is at-least-once, so a redelivery must not duplicate the point."""
    await upload_and_run(upload_source_file, send_command, make_csv_bytes(rows=1))
    command = ProjectEventCommand(
        message_id=UUID(int=0),
        event_type="QAPairAdded",
        payload='{"external_id": {"value": "q-0"}}',
    )

    await send_command(command)
    await send_command(command)

    found = await retriever.retrieve(
        SearchCriteria(query=SearchQuery(content="Question 0?"), top_k=TopK(value=10)),
    )

    assert [candidate.external_id for candidate in found].count(
        ExternalId(value="q-0"),
    ) == 1
