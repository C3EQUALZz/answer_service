from collections import deque
from collections.abc import Awaitable, Callable, Sequence
from typing import Any

import pytest

from answer_service.application.commands.analytics.record_query.handler import (
    RecordQueryHandler,
)
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
from answer_service.application.common.mediator.handlers import CommandHandler
from answer_service.application.common.mediator.markers import Command
from answer_service.application.common.ports.outbox import OutboxMessage
from answer_service.application.common.ports.source_file.source_row import SourceRow
from answer_service.application.pipelines.events_pipeline import EventsPipeline
from answer_service.application.pipelines.transaction_pipeline import (
    TransactionPipeline,
)
from answer_service.application.queries.analytics.get_statistics.handler import (
    GetStatisticsHandler,
)
from answer_service.application.queries.analytics.list_unanswered_queries.handler import (
    ListUnansweredQueriesHandler,
)
from answer_service.application.queries.indexing.get_indexing_task.handler import (
    GetIndexingTaskHandler,
)
from answer_service.domain.analytics.factories.query_log_factory import QueryLogFactory
from answer_service.domain.common.events_collection import EventsCollection
from answer_service.domain.indexing.entities.indexing_task import IndexingTask
from answer_service.domain.indexing.factories.indexing_task_factory import (
    IndexingTaskFactory,
)
from answer_service.domain.indexing.factories.qa_pair_factory import QAPairFactory
from answer_service.domain.indexing.services.sync_planner import SyncPlanner
from tests.unit.factories.domain_factories import make_source_reference, make_task_id
from tests.unit.factories.handler_factories import (
    EnqueueIndexingHandlerBuilder,
    RunIndexingHandlerBuilder,
    create_enqueue_indexing_handler,
    create_project_event_handler,
    create_relay_outbox_handler,
    create_run_indexing_handler,
)
from tests.unit.factories.outbox_factories import make_outbox_message
from tests.unit.stubs.gateways import (
    InMemoryAnalytics,
    InMemoryIndexingTaskGateway,
    InMemoryIndexingTaskQueryGateway,
    InMemoryOutboxGateway,
    InMemoryQACatalog,
)
from tests.unit.stubs.infrastructure import (
    CallJournal,
    RecordingEventBus,
    RecordingOutboxPublisher,
    RecordingSearchIndexWriter,
    RecordingTaskScheduler,
    RecordingTransactionManager,
    StubQueryLogIdGenerator,
    StubTaskIdGenerator,
)
from tests.unit.stubs.source_file import StubSourceFileStorage

type PipelineRunner = Callable[
    [Command[Any], CommandHandler[Any, Any]],
    Awaitable[Any],
]
type OutboxSeeder = Callable[[int], Awaitable[list[OutboxMessage]]]


@pytest.fixture()
def journal() -> CallJournal:
    return CallJournal()


@pytest.fixture()
def events_collection() -> EventsCollection:
    """One request-scoped collection, shared by every aggregate in a test."""
    return EventsCollection(events=deque())


@pytest.fixture()
def transaction_manager(journal: CallJournal) -> RecordingTransactionManager:
    return RecordingTransactionManager(journal)


@pytest.fixture()
def event_bus(journal: CallJournal) -> RecordingEventBus:
    return RecordingEventBus(journal)


@pytest.fixture()
def task_gateway() -> InMemoryIndexingTaskGateway:
    return InMemoryIndexingTaskGateway()


@pytest.fixture()
def catalog() -> InMemoryQACatalog:
    return InMemoryQACatalog()


@pytest.fixture()
def outbox_gateway() -> InMemoryOutboxGateway:
    return InMemoryOutboxGateway()


@pytest.fixture()
def outbox_publisher() -> RecordingOutboxPublisher:
    return RecordingOutboxPublisher()


@pytest.fixture()
def task_scheduler() -> RecordingTaskScheduler:
    return RecordingTaskScheduler()


@pytest.fixture()
def source_storage() -> StubSourceFileStorage:
    return StubSourceFileStorage(make_source_reference())


@pytest.fixture()
def task_id_generator() -> StubTaskIdGenerator:
    return StubTaskIdGenerator(make_task_id())


@pytest.fixture()
def qa_pair_factory(events_collection: EventsCollection) -> QAPairFactory:
    return QAPairFactory(events_collection)


@pytest.fixture()
def indexing_task_factory(
    events_collection: EventsCollection,
    task_id_generator: StubTaskIdGenerator,
) -> IndexingTaskFactory:
    return IndexingTaskFactory(events_collection, task_id_generator)


@pytest.fixture()
def sync_planner() -> SyncPlanner:
    return SyncPlanner()


@pytest.fixture()
async def queued_task(
    task_gateway: InMemoryIndexingTaskGateway,
    indexing_task_factory: IndexingTaskFactory,
) -> IndexingTask:
    task = indexing_task_factory.create(source=make_source_reference())
    await task_gateway.add(task)
    return task


@pytest.fixture()
async def running_task(
    task_gateway: InMemoryIndexingTaskGateway,
    indexing_task_factory: IndexingTaskFactory,
) -> IndexingTask:
    """A task in the state ``run_indexing`` expects to find it in."""
    task = indexing_task_factory.create(source=make_source_reference())
    task.start()
    await task_gateway.add(task)
    return task


@pytest.fixture()
def run_indexing_handler(
    task_gateway: InMemoryIndexingTaskGateway,
    catalog: InMemoryQACatalog,
    source_storage: StubSourceFileStorage,
    qa_pair_factory: QAPairFactory,
    sync_planner: SyncPlanner,
) -> RunIndexingHandlerBuilder:
    """Builds the handler once the test has chosen the source rows."""

    def build(rows: Sequence[SourceRow] = ()) -> RunIndexingHandler:
        return create_run_indexing_handler(
            rows,
            task_gateway=task_gateway,
            catalog=catalog,
            source_storage=source_storage,
            qa_pair_factory=qa_pair_factory,
            sync_planner=sync_planner,
        )

    return build


@pytest.fixture()
def enqueue_indexing_handler(
    task_gateway: InMemoryIndexingTaskGateway,
    indexing_task_factory: IndexingTaskFactory,
    source_storage: StubSourceFileStorage,
) -> EnqueueIndexingHandlerBuilder:
    """Builds the handler once the test has chosen whether the file is valid."""

    def build(*, rejects: bool = False) -> EnqueueIndexingHandler:
        return create_enqueue_indexing_handler(
            task_gateway=task_gateway,
            indexing_task_factory=indexing_task_factory,
            source_storage=source_storage,
            rejects=rejects,
        )

    return build


@pytest.fixture()
def seed_outbox(outbox_gateway: InMemoryOutboxGateway) -> OutboxSeeder:
    """Fills the outbox with pending messages and returns them in order."""

    async def seed(count: int) -> list[OutboxMessage]:
        messages = [make_outbox_message() for _ in range(count)]
        for message in messages:
            await outbox_gateway.add(message)
        return messages

    return seed


@pytest.fixture()
def relay_outbox_handler(
    outbox_gateway: InMemoryOutboxGateway,
    outbox_publisher: RecordingOutboxPublisher,
) -> RelayOutboxHandler:
    return create_relay_outbox_handler(
        outbox_gateway=outbox_gateway,
        outbox_publisher=outbox_publisher,
    )


@pytest.fixture()
def pipeline_runner(
    transaction_manager: RecordingTransactionManager,
    events_collection: EventsCollection,
    event_bus: RecordingEventBus,
) -> PipelineRunner:
    """Runs a handler wrapped in the production pipeline order.

    ``TransactionPipeline -> EventsPipeline -> handler``, so events are drained
    inside the transaction and a raising handler rolls back without publishing.
    """

    async def run(command: Command[Any], handler: CommandHandler[Any, Any]) -> Any:
        events_pipeline = EventsPipeline[Any, Any](events_collection, event_bus)
        transaction_pipeline = TransactionPipeline[Any, Any](transaction_manager)
        return await transaction_pipeline.handle(
            command,
            lambda request: events_pipeline.handle(request, handler.handle),
        )

    return run


@pytest.fixture()
def index_writer() -> RecordingSearchIndexWriter:
    return RecordingSearchIndexWriter()


@pytest.fixture()
def project_event_handler(
    catalog: InMemoryQACatalog,
    index_writer: RecordingSearchIndexWriter,
) -> ProjectEventHandler:
    return create_project_event_handler(catalog=catalog, index_writer=index_writer)


@pytest.fixture()
def analytics() -> InMemoryAnalytics:
    return InMemoryAnalytics()


@pytest.fixture()
def task_query_gateway() -> InMemoryIndexingTaskQueryGateway:
    return InMemoryIndexingTaskQueryGateway()


@pytest.fixture()
def query_log_id_generator() -> StubQueryLogIdGenerator:
    return StubQueryLogIdGenerator()


@pytest.fixture()
def query_log_factory(
    query_log_id_generator: StubQueryLogIdGenerator,
) -> QueryLogFactory:
    return QueryLogFactory(query_log_id_generator)


@pytest.fixture()
def record_query_handler(
    query_log_factory: QueryLogFactory,
    analytics: InMemoryAnalytics,
) -> RecordQueryHandler:
    return RecordQueryHandler(query_log_factory, analytics)


@pytest.fixture()
def get_indexing_task_handler(
    task_query_gateway: InMemoryIndexingTaskQueryGateway,
) -> GetIndexingTaskHandler:
    return GetIndexingTaskHandler(task_query_gateway)


@pytest.fixture()
def get_statistics_handler(
    catalog: InMemoryQACatalog,
    analytics: InMemoryAnalytics,
) -> GetStatisticsHandler:
    return GetStatisticsHandler(catalog, analytics)


@pytest.fixture()
def list_unanswered_handler(
    analytics: InMemoryAnalytics,
) -> ListUnansweredQueriesHandler:
    return ListUnansweredQueriesHandler(analytics)
