"""Integration test topology.

    PostgresContainer ──► PostgresConfig / SQLAlchemyConfig ──┐
                                                              ├──► dishka container
    in-memory Qdrant + fake embeddings ───────────────────────┘
                                │
                          FastAPI app ──► AsyncClient (per test)

The production providers are reused unchanged; only the vector store is swapped
(see ``tests/integration/ioc.py``). Every test starts against empty tables:
truncating is what keeps a test from passing on rows another one left behind.
"""

from collections.abc import AsyncIterator, Iterator
from datetime import datetime
from typing import Final

import pytest
from dishka import AsyncContainer, Scope, make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response
from qdrant_client import QdrantClient
from qdrant_client.models import Filter
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from taskiq import AsyncBroker
from testcontainers.postgres import PostgresContainer

from answer_service.application.common.mediator.markers import BaseRequest
from answer_service.application.common.mediator.sender import Sender
from answer_service.application.common.ports.gateways import (
    AnalyticsCommandGateway,
    IndexingTaskCommandGateway,
    QACatalogCommandGateway,
)
from answer_service.application.common.ports.outbox import (
    OutboxCommandGateway,
    OutboxMessage,
)
from answer_service.application.common.ports.transaction_manager import (
    TransactionManager,
)
from answer_service.domain.analytics.value_objects.query_execution import QueryExecution
from answer_service.domain.analytics.value_objects.query_kind import QueryKind
from answer_service.domain.indexing.entities.indexing_task import IndexingTask
from answer_service.domain.indexing.entities.qa_pair import QAPair
from answer_service.domain.indexing.value_objects.external_id import ExternalId
from answer_service.domain.indexing.value_objects.task_id import TaskId
from answer_service.infrastructure.persistence.models.base import metadata
from answer_service.setup.bootstrap.loaders.search_config_loader import MIN_COSINE
from answer_service.setup.bootstrap.setups.database_setup import setup_map_tables
from answer_service.setup.bootstrap.setups.http_setup import (
    setup_exc_handlers,
    setup_http_routes,
)
from answer_service.setup.bootstrap.setups.task_manager_setup import (
    setup_task_manager_tasks,
)
from answer_service.setup.configs.alchemy_config import SQLAlchemyConfig
from answer_service.setup.configs.asgi_config import ASGIConfig
from answer_service.setup.configs.indexing_config import IndexingConfig
from answer_service.setup.configs.mistral_config import MistralConfig
from answer_service.setup.configs.nats_config import NatsConfig
from answer_service.setup.configs.postgres_config import PostgresConfig
from answer_service.setup.configs.qdrant_config import QdrantConfig
from answer_service.setup.configs.redis_config import RedisConfig
from answer_service.setup.configs.search_config import SearchConfig
from answer_service.setup.configs.storage_config import StorageConfig
from answer_service.setup.configs.taskiq_config import TaskIQConfig
from tests.integration.arrange import (
    CommandSender,
    OutboxSeeder,
    PairBuilder,
    PairStorer,
    QueryLogStorer,
    SourceFileUploader,
    TaskStorer,
)
from tests.integration.brokers import RecordingBroker
from tests.integration.ioc import test_app_providers
from tests.unit.factories.domain_factories import (
    SOURCE_UPDATED_AT,
    make_events_collection,
    make_qa_content,
    make_query_log,
)
from tests.unit.factories.outbox_factories import make_outbox_message

POSTGRES_IMAGE: Final[str] = "postgres:16-alpine"
UPLOAD_URL: Final[str] = "/v1/indexing/upload"

# Session-scoped async fixtures and the tests must share one loop, or the engine
# is created on a loop that is gone by the time a test uses it.
pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.fixture(scope="session")
def postgres_container() -> Iterator[PostgresContainer]:
    """One database for the whole session — starting a container per test is slow."""
    with PostgresContainer(POSTGRES_IMAGE, driver="asyncpg") as container:
        yield container


@pytest.fixture(scope="session")
def postgres_config(postgres_container: PostgresContainer) -> PostgresConfig:
    return PostgresConfig(
        user=postgres_container.username,
        password=postgres_container.password,
        host=postgres_container.get_container_host_ip(),
        port=int(postgres_container.get_exposed_port(5432)),
        db_name=postgres_container.dbname,
        driver="asyncpg",
    )


@pytest.fixture(scope="session")
def alchemy_config() -> SQLAlchemyConfig:
    return SQLAlchemyConfig(
        pool_pre_ping=True,
        pool_recycle=3600,
        pool_size=5,
        max_overflow=10,
        echo=False,
    )


@pytest.fixture(scope="session")
def broker() -> RecordingBroker:
    """The production tasks on a broker that records instead of executing."""
    recording_broker = RecordingBroker()
    setup_task_manager_tasks(recording_broker)
    return recording_broker


@pytest.fixture(autouse=True)
def _isolate_scheduled_tasks(broker: RecordingBroker) -> Iterator[None]:
    """Clears the scheduling record around every test.

    Autouse because the broker outlives the session: without it a test could
    pass on a task its neighbour scheduled.
    """
    broker.forget_kicked()
    yield
    broker.forget_kicked()


@pytest.fixture(scope="session")
def container_context(
    postgres_config: PostgresConfig,
    alchemy_config: SQLAlchemyConfig,
    broker: RecordingBroker,
    tmp_path_factory: pytest.TempPathFactory,
) -> dict[type, object]:
    return {
        ASGIConfig: ASGIConfig(),
        PostgresConfig: postgres_config,
        SQLAlchemyConfig: alchemy_config,
        NatsConfig: NatsConfig(host="localhost", port=4222),
        RedisConfig: RedisConfig(host="localhost", port=6379),
        TaskIQConfig: TaskIQConfig(),
        MistralConfig: MistralConfig(api_key="test-key"),
        QdrantConfig: QdrantConfig(host="localhost", collection_name="qa_pairs_test"),
        # The dense floor is disabled rather than tuned: the fake embedding
        # model produces unrelated vectors, so a similarity against it means
        # nothing and any real floor would reject every candidate. The lexical
        # floor is left at its production value, where the scores are genuine.
        IndexingConfig: IndexingConfig(),
        SearchConfig: SearchConfig(dense_score_floor=MIN_COSINE),
        StorageConfig: StorageConfig(directory=tmp_path_factory.mktemp("uploads")),
        AsyncBroker: broker,
    }


@pytest.fixture(scope="session")
async def container(
    container_context: dict[type, object],
) -> AsyncIterator[AsyncContainer]:
    setup_map_tables()
    async_container = make_async_container(
        *test_app_providers(),
        context=container_context,
    )
    yield async_container
    await async_container.close()


@pytest.fixture(scope="session")
async def engine(container: AsyncContainer) -> AsyncEngine:
    """The container's own engine, so tests and the app share one database."""
    return await container.get(AsyncEngine)


@pytest.fixture(scope="session")
async def _schema(engine: AsyncEngine) -> AsyncIterator[None]:
    """Creates the schema from the mapped metadata.

    Not by running alembic: these tests check that the *mappings* work, and
    building the schema from the same metadata the mappers use keeps a
    migration lag from failing them for the wrong reason.
    """
    async with engine.begin() as connection:
        await connection.run_sync(metadata.create_all)
    yield
    async with engine.begin() as connection:
        await connection.run_sync(metadata.drop_all)


@pytest.fixture()
async def clean_tables(
    _schema: None,
    engine: AsyncEngine,
    container: AsyncContainer,
) -> None:
    """Empties every table and the vector store before each test.

    Requested with ``pytest.mark.usefixtures`` rather than as an argument: the
    test never touches its value, only its effect. Truncating up front rather
    than cleaning up afterwards means a test that fails leaves its rows behind
    to be inspected.

    The vector store is cleared here too, and not because a test asked. It is
    application-scoped, so points projected by one test survive into every test
    after it — which shows up as a later test finding a pair it never indexed.
    """
    tables = ", ".join(table.name for table in metadata.sorted_tables)
    async with engine.begin() as connection:
        await connection.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))

    qdrant_config = await container.get(QdrantConfig)
    qdrant_client = await container.get(QdrantClient)
    if qdrant_client.collection_exists(qdrant_config.collection_name):
        qdrant_client.delete(
            collection_name=qdrant_config.collection_name,
            points_selector=Filter(must=[]),
        )


@pytest.fixture()
async def arrange_scope(container: AsyncContainer) -> AsyncIterator[AsyncContainer]:
    """A request scope for arranging state, separate from the one under test.

    Separate on purpose: a test that reads through its own scope must not be
    handed the very session that wrote the rows, or nothing about visibility,
    locking or flushing would be exercised.
    """
    async with container(scope=Scope.REQUEST) as request_container:
        yield request_container


@pytest.fixture()
async def arrange_transaction(arrange_scope: AsyncContainer) -> TransactionManager:
    resolved: TransactionManager = await arrange_scope.get(TransactionManager)
    return resolved


@pytest.fixture()
async def arrange_outbox(arrange_scope: AsyncContainer) -> OutboxCommandGateway:
    resolved: OutboxCommandGateway = await arrange_scope.get(OutboxCommandGateway)
    return resolved


@pytest.fixture()
async def arrange_indexing_tasks(
    arrange_scope: AsyncContainer,
) -> IndexingTaskCommandGateway:
    resolved: IndexingTaskCommandGateway = await arrange_scope.get(
        IndexingTaskCommandGateway
    )
    return resolved


@pytest.fixture()
async def arrange_catalog(arrange_scope: AsyncContainer) -> QACatalogCommandGateway:
    resolved: QACatalogCommandGateway = await arrange_scope.get(QACatalogCommandGateway)
    return resolved


@pytest.fixture()
async def arrange_analytics(arrange_scope: AsyncContainer) -> AnalyticsCommandGateway:
    resolved: AnalyticsCommandGateway = await arrange_scope.get(AnalyticsCommandGateway)
    return resolved


@pytest.fixture()
def dishka_container(container: AsyncContainer) -> AsyncContainer:
    """The container the ``inject`` decorator opens a request scope from.

    Named for the keyword ``inject`` looks up; tests never reference it
    directly, they declare ``FromDishka[SomePort]`` instead.
    """
    return container


@pytest.fixture()
def app(container: AsyncContainer) -> FastAPI:
    fastapi_app = FastAPI()
    setup_http_routes(fastapi_app)
    setup_exc_handlers(fastapi_app)
    setup_dishka(container, fastapi_app)
    return fastapi_app


@pytest.fixture()
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as async_client:
        yield async_client


@pytest.fixture()
def store_outbox_messages(
    arrange_outbox: OutboxCommandGateway,
    arrange_transaction: TransactionManager,
) -> OutboxSeeder:
    """Commits pending messages before the test reads them.

    Written against the ports, not the container: what a test arranges is
    "messages exist", and how they get there is the container's business.
    """

    async def store(count: int) -> list[OutboxMessage]:
        messages = [make_outbox_message() for _ in range(count)]
        for message in messages:
            await arrange_outbox.add(message)
        await arrange_transaction.commit()
        return messages

    return store


@pytest.fixture()
def store_indexing_task(
    arrange_indexing_tasks: IndexingTaskCommandGateway,
    arrange_transaction: TransactionManager,
) -> TaskStorer:
    """Commits a task before the test reads it back."""

    async def store(task: IndexingTask) -> TaskId:
        await arrange_indexing_tasks.add(task)
        await arrange_transaction.commit()
        return task.id

    return store


@pytest.fixture()
def make_pair() -> PairBuilder:
    """Builds a registered pair with its own events collection."""

    def build(external_id: str, **content: str) -> QAPair:
        return QAPair.register(
            external_id=ExternalId(value=external_id),
            content=make_qa_content(**content),
            source_updated_at=SOURCE_UPDATED_AT,
            events_collection=make_events_collection(),
        )

    return build


@pytest.fixture()
def store_qa_pairs(
    arrange_catalog: QACatalogCommandGateway,
    arrange_transaction: TransactionManager,
) -> PairStorer:
    async def store(*pairs: QAPair) -> None:
        for pair in pairs:
            await arrange_catalog.add(pair)
        await arrange_transaction.commit()

    return store


@pytest.fixture()
def store_query_log(
    arrange_analytics: AnalyticsCommandGateway,
    arrange_transaction: TransactionManager,
) -> QueryLogStorer:
    """Records one served query, committed before the test reads it."""

    async def store(
        text: str = "how do I reset my password?",
        *,
        results_count: int = 3,
        latency_ms: int = 42,
        occurred_at: datetime | None = None,
        kind: QueryKind = QueryKind.SEARCH,
        category: str | None = None,
        execution: QueryExecution | None = None,
    ) -> None:
        log = make_query_log(
            text,
            results_count=results_count,
            latency_ms=latency_ms,
            kind=kind,
            category=category,
            occurred_at=occurred_at,
            execution=execution,
        )
        await arrange_analytics.add(log)
        await arrange_transaction.commit()

    return store


@pytest.fixture()
def upload_source_file(client: AsyncClient) -> SourceFileUploader:
    """Posts a source file the way a client would."""

    async def upload(
        content: bytes,
        filename: str = "faq.csv",
        content_type: str = "text/csv",
    ) -> Response:
        return await client.post(
            UPLOAD_URL,
            files={"file": (filename, content, content_type)},
        )

    return upload


@pytest.fixture()
def send_command(container: AsyncContainer) -> CommandSender:
    """Dispatches a command the way the worker does: one request scope each.

    A scope per command on purpose — every worker step commits independently,
    which is what lets a failed sync still record its failure.
    """

    async def send[TResponse](command: BaseRequest[TResponse]) -> TResponse:
        async with container(scope=Scope.REQUEST) as request_container:
            sender: Sender = await request_container.get(Sender)
            response: TResponse = await sender.send(command)
            return response

    return send
