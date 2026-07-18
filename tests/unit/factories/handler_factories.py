"""Assembly of command handlers from their stubbed collaborators.

Keeping the wiring here means a test names only the collaborator it asserts on;
adding a dependency to a handler touches one function instead of every test.
"""

from collections.abc import Sequence
from typing import Protocol

from answer_service.application.commands.indexing.enqueue_indexing.handler import (
    EnqueueIndexingHandler,
)
from answer_service.application.commands.indexing.run_indexing.handler import (
    RunIndexingHandler,
)
from answer_service.application.commands.outbox.relay_outbox.handler import (
    RelayOutboxHandler,
)
from answer_service.application.commands.search.project_event.handler import (
    ProjectEventHandler,
)
from answer_service.application.common.ports.source_file.source_row import SourceRow
from answer_service.domain.indexing.factories.indexing_task_factory import (
    IndexingTaskFactory,
)
from answer_service.domain.indexing.factories.qa_pair_factory import QAPairFactory
from answer_service.domain.indexing.services.sync_planner import SyncPlanner
from tests.unit.stubs.gateways import (
    InMemoryIndexingTaskGateway,
    InMemoryOutboxGateway,
    InMemoryQACatalog,
)
from tests.unit.stubs.infrastructure import (
    RecordingOutboxPublisher,
    RecordingSearchIndexWriter,
    RecordingTaskScheduler,
)
from tests.unit.stubs.source_file import (
    StubSourceFileReader,
    StubSourceFileStorage,
)


def create_run_indexing_handler(
    rows: Sequence[SourceRow],
    *,
    task_gateway: InMemoryIndexingTaskGateway,
    catalog: InMemoryQACatalog,
    source_storage: StubSourceFileStorage,
    qa_pair_factory: QAPairFactory,
    sync_planner: SyncPlanner,
) -> RunIndexingHandler:
    return RunIndexingHandler(
        task_gateway=task_gateway,
        source_storage=source_storage,
        source_reader=StubSourceFileReader(rows),
        catalog_command=catalog,
        catalog_query=catalog,
        qa_pair_factory=qa_pair_factory,
        sync_planner=sync_planner,
    )


def create_enqueue_indexing_handler(
    *,
    task_gateway: InMemoryIndexingTaskGateway,
    task_scheduler: RecordingTaskScheduler,
    indexing_task_factory: IndexingTaskFactory,
    source_storage: StubSourceFileStorage,
    rejects: bool = False,
) -> EnqueueIndexingHandler:
    return EnqueueIndexingHandler(
        source_reader=StubSourceFileReader(rejects=rejects),
        source_storage=source_storage,
        task_factory=indexing_task_factory,
        task_gateway=task_gateway,
        task_scheduler=task_scheduler,
    )


def create_relay_outbox_handler(
    *,
    outbox_gateway: InMemoryOutboxGateway,
    outbox_publisher: RecordingOutboxPublisher,
) -> RelayOutboxHandler:
    return RelayOutboxHandler(outbox_gateway, outbox_publisher)


class RunIndexingHandlerBuilder(Protocol):
    """Signature of the ``run_indexing_handler`` fixture."""

    def __call__(self, rows: Sequence[SourceRow] = ()) -> RunIndexingHandler: ...


class EnqueueIndexingHandlerBuilder(Protocol):
    """Signature of the ``enqueue_indexing_handler`` fixture."""

    def __call__(self, *, rejects: bool = False) -> EnqueueIndexingHandler: ...


def create_project_event_handler(
    *,
    catalog: InMemoryQACatalog,
    index_writer: RecordingSearchIndexWriter,
) -> ProjectEventHandler:
    return ProjectEventHandler(catalog, index_writer)
