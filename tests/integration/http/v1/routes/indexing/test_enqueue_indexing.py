"""Uploading a source file, through the real application.

Everything below the route is real: the mediator, both pipelines, the session,
the outbox and the scheduler. Only the vector store is a double, and the task
bodies are inert.

State is asserted through the application's own ports, never through SQL — the
route's contract is what the service records, not which table it lands in.
"""

from uuid import UUID

import pytest
from dishka import FromDishka

from answer_service.application.common.ports.gateways import IndexingTaskQueryGateway
from answer_service.application.common.ports.outbox import OutboxCommandGateway
from answer_service.domain.indexing.value_objects.task_id import TaskId
from answer_service.domain.indexing.value_objects.task_status import IndexingTaskStatus
from tests.integration.arrange import SourceFileUploader
from tests.integration.brokers import RecordingBroker
from tests.integration.inject import inject
from tests.unit.factories.source_file_factories import (
    make_csv_bytes,
    make_csv_bytes_without,
    make_excel_bytes,
)

pytestmark = [
    pytest.mark.asyncio(loop_scope="session"),
    pytest.mark.usefixtures("clean_tables"),
]


async def test_a_csv_upload_is_accepted(
    upload_source_file: SourceFileUploader,
) -> None:
    response = await upload_source_file(make_csv_bytes(rows=3))

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == IndexingTaskStatus.QUEUED.value
    assert UUID(body["task_id"])


async def test_an_excel_upload_is_accepted(
    upload_source_file: SourceFileUploader,
) -> None:
    """The bug that shipped: Excel validated on upload but failed in the worker."""
    response = await upload_source_file(make_excel_bytes(rows=2), filename="faq.xlsx")

    assert response.status_code == 202


@inject
async def test_the_task_is_recorded_as_queued(
    upload_source_file: SourceFileUploader,
    task_query: FromDishka[IndexingTaskQueryGateway],
) -> None:
    response = await upload_source_file(make_csv_bytes())

    view = await task_query.read_by_id(TaskId(UUID(response.json()["task_id"])))

    assert view is not None
    assert view.status is IndexingTaskStatus.QUEUED
    assert not view.is_finished


@inject
async def test_the_queued_event_reaches_the_outbox(
    upload_source_file: SourceFileUploader,
    outbox: FromDishka[OutboxCommandGateway],
) -> None:
    """The event must be written in the same transaction as the task itself."""
    await upload_source_file(make_csv_bytes())

    pending = await outbox.read_pending(limit=10)

    assert [message.event_type for message in pending] == ["IndexingTaskQueued"]


async def test_the_upload_schedules_nothing_of_its_own(
    upload_source_file: SourceFileUploader,
    broker: RecordingBroker,
) -> None:
    """Scheduling from inside the request raced its own commit.

    The work is started by the relay once the row is visible, so the only thing
    the request leaves behind is the outbox message asserted above.
    """
    await upload_source_file(make_csv_bytes())

    assert broker.kicked_task_names == []


async def test_a_file_with_a_missing_column_is_rejected(
    upload_source_file: SourceFileUploader,
) -> None:
    response = await upload_source_file(make_csv_bytes_without("answer"))

    assert response.status_code == 422
    assert "answer" in response.json()["description"]


async def test_a_file_that_is_not_a_source_file_is_rejected(
    upload_source_file: SourceFileUploader,
) -> None:
    response = await upload_source_file(b"%PDF-1.4 not a table", filename="notes.pdf")

    assert response.status_code == 415


@inject
async def test_a_rejected_upload_leaves_nothing_behind(
    upload_source_file: SourceFileUploader,
    outbox: FromDishka[OutboxCommandGateway],
) -> None:
    """Validation is the fail-fast gate: nothing may be persisted behind it."""
    await upload_source_file(make_csv_bytes_without("answer"))

    assert await outbox.read_pending(limit=10) == []


@inject
async def test_two_uploads_produce_two_independent_tasks(
    upload_source_file: SourceFileUploader,
    task_query: FromDishka[IndexingTaskQueryGateway],
) -> None:
    first = await upload_source_file(make_csv_bytes())
    second = await upload_source_file(make_csv_bytes())

    first_id = TaskId(UUID(first.json()["task_id"]))
    second_id = TaskId(UUID(second.json()["task_id"]))

    assert first_id != second_id
    assert await task_query.read_by_id(first_id) is not None
    assert await task_query.read_by_id(second_id) is not None
