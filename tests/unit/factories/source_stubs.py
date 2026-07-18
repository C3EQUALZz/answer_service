from answer_service.setup.bootstrap.sources.alchemy_env_source_factory import (
    SQLAlchemyEnvSourceFactory,
)
from answer_service.setup.bootstrap.sources.asgi_env_source_factory import (
    ASGIEnvSourceFactory,
)
from answer_service.setup.bootstrap.sources.logging_env_source_factory import (
    LoggingEnvSourceFactory,
)
from answer_service.setup.bootstrap.sources.mistral_env_source_factory import (
    MistralEnvSourceFactory,
)
from answer_service.setup.bootstrap.sources.nats_env_source_factory import (
    NatsEnvSourceFactory,
)
from answer_service.setup.bootstrap.sources.postgres_env_source_factory import (
    PostgresEnvSourceFactory,
)
from answer_service.setup.bootstrap.sources.qdrant_env_source_factory import (
    QdrantEnvSourceFactory,
)
from answer_service.setup.bootstrap.sources.redis_env_source_factory import (
    RedisEnvSourceFactory,
)
from answer_service.setup.bootstrap.sources.storage_env_source_factory import (
    StorageEnvSourceFactory,
)
from answer_service.setup.bootstrap.sources.taskiq_env_source_factory import (
    TaskIQEnvSourceFactory,
)
from tests.unit.factories.env_data_factories import (
    asgi_env,
    logging_env,
    mistral_env,
    nats_env,
    postgres_env,
    qdrant_env,
    redis_env,
    sqlalchemy_env,
    storage_env,
    taskiq_env,
)
from tests.unit.factories.stub_source_factory import StubSourceFactory


def asgi_source_stub(**overrides: str) -> StubSourceFactory:
    """In-memory stub serving valid ``UVICORN_*`` / ``FASTAPI_*`` values."""
    return StubSourceFactory.mirroring(
        ASGIEnvSourceFactory(),
        asgi_env(**overrides),
    )


def postgres_source_stub(**overrides: str) -> StubSourceFactory:
    """In-memory stub serving valid ``POSTGRES_*`` values; override any key."""
    return StubSourceFactory.mirroring(
        PostgresEnvSourceFactory(),
        postgres_env(**overrides),
    )


def sqlalchemy_source_stub(**overrides: str) -> StubSourceFactory:
    """In-memory stub serving valid ``DB_*`` values; override any key."""
    return StubSourceFactory.mirroring(
        SQLAlchemyEnvSourceFactory(),
        sqlalchemy_env(**overrides),
    )


def logging_source_stub(**overrides: str) -> StubSourceFactory:
    """In-memory stub serving valid logging values; override any key."""
    return StubSourceFactory.mirroring(
        LoggingEnvSourceFactory(),
        logging_env(**overrides),
    )


def empty_logging_source_stub() -> StubSourceFactory:
    """In-memory stub serving no values, so every field falls back to default."""
    return StubSourceFactory.mirroring(LoggingEnvSourceFactory(), {})


def nats_source_stub(**overrides: str) -> StubSourceFactory:
    """In-memory stub serving valid ``NATS_*`` values; override any key."""
    return StubSourceFactory.mirroring(NatsEnvSourceFactory(), nats_env(**overrides))


def redis_source_stub(**overrides: str) -> StubSourceFactory:
    """In-memory stub serving valid ``REDIS_*`` values; override any key."""
    return StubSourceFactory.mirroring(RedisEnvSourceFactory(), redis_env(**overrides))


def taskiq_source_stub(**overrides: str) -> StubSourceFactory:
    """In-memory stub serving valid ``TASKIQ_*`` values; override any key."""
    return StubSourceFactory.mirroring(TaskIQEnvSourceFactory(), taskiq_env(**overrides))


def mistral_source_stub(**overrides: str) -> StubSourceFactory:
    """In-memory stub serving valid ``MISTRAL_*`` values; override any key."""
    return StubSourceFactory.mirroring(
        MistralEnvSourceFactory(),
        mistral_env(**overrides),
    )


def qdrant_source_stub(**overrides: str) -> StubSourceFactory:
    """In-memory stub serving valid ``QDRANT_*`` values; override any key."""
    return StubSourceFactory.mirroring(QdrantEnvSourceFactory(), qdrant_env(**overrides))


def storage_source_stub(**overrides: str) -> StubSourceFactory:
    """In-memory stub serving valid storage values; override any key."""
    return StubSourceFactory.mirroring(
        StorageEnvSourceFactory(),
        storage_env(**overrides),
    )
