import pytest

from answer_service.application.common.ports.task_manager import RunIndexingPayload
from answer_service.application.error import UnsupportedSourceFormatError
from answer_service.domain.indexing.value_objects.task_status import IndexingTaskStatus
from tests.unit.factories.command_factories import make_enqueue_indexing_command
from tests.unit.factories.domain_factories import (
    make_source_reference,
    make_task_id,
)
from tests.unit.factories.handler_factories import EnqueueIndexingHandlerBuilder
from tests.unit.stubs.gateways import InMemoryIndexingTaskGateway
from tests.unit.stubs.infrastructure import RecordingTaskScheduler
from tests.unit.stubs.source_file import StubSourceFileStorage


async def test_persists_queued_task_and_schedules_the_worker(
    task_gateway: InMemoryIndexingTaskGateway,
    task_scheduler: RecordingTaskScheduler,
    enqueue_indexing_handler: EnqueueIndexingHandlerBuilder,
) -> None:
    handler = enqueue_indexing_handler()

    response = await handler.handle(make_enqueue_indexing_command())

    assert response.task_id == make_task_id()
    assert response.status is IndexingTaskStatus.QUEUED
    assert task_gateway.tasks[response.task_id].source == make_source_reference()

    scheduled_id, payload = task_scheduler.scheduled[0]
    assert scheduled_id == f"indexing:{response.task_id}"
    assert isinstance(payload, RunIndexingPayload)
    assert payload.task_id == response.task_id


async def test_rejects_a_bad_file_before_touching_storage_or_the_queue(
    task_gateway: InMemoryIndexingTaskGateway,
    task_scheduler: RecordingTaskScheduler,
    source_storage: StubSourceFileStorage,
    enqueue_indexing_handler: EnqueueIndexingHandlerBuilder,
) -> None:
    """Validation is the fail-fast gate: nothing may be persisted behind it."""
    handler = enqueue_indexing_handler(rejects=True)

    with pytest.raises(UnsupportedSourceFormatError):
        await handler.handle(make_enqueue_indexing_command())

    assert source_storage.saved == []
    assert task_gateway.tasks == {}
    assert task_scheduler.scheduled == []
