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
from typing import Final

import pytest
from dishka import AsyncContainer, Scope, make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from taskiq import AsyncBroker
from testcontainers.postgres import PostgresContainer

from answer_service.application.common.ports.gateways import (
    IndexingTaskCommandGateway,
    QACatalogCommandGateway,
)
from answer_service.application.common.ports.outbox import OutboxCommandGateway
from answer_service.application.common.ports.transaction_manager import (
    TransactionManager,
)
from answer_service.infrastructure.persistence.models.base import metadata
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
from answer_service.setup.configs.mistral_config import MistralConfig
from answer_service.setup.configs.nats_config import NatsConfig
from answer_service.setup.configs.postgres_config import PostgresConfig
from answer_service.setup.configs.qdrant_config import QdrantConfig
from answer_service.setup.configs.redis_config import RedisConfig
from answer_service.setup.configs.storage_config import StorageConfig
from answer_service.setup.configs.taskiq_config import TaskIQConfig
from tests.integration.brokers import RecordingBroker
from tests.integration.ioc import test_app_providers

POSTGRES_IMAGE: Final[str] = "postgres:16-alpine"

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
async def clean_tables(_schema: None, engine: AsyncEngine) -> None:
    """Empties every table before each test.

    Requested with ``pytest.mark.usefixtures`` rather than as an argument: the
    test never touches its value, only its effect. Truncating up front rather
    than cleaning up afterwards means a test that fails leaves its rows behind
    to be inspected.
    """
    tables = ", ".join(table.name for table in metadata.sorted_tables)
    async with engine.begin() as connection:
        await connection.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


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
