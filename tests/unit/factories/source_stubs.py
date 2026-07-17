from answer_service.setup.bootstrap.sources.alchemy_env_source_factory import (
    SQLAlchemyEnvSourceFactory,
)
from answer_service.setup.bootstrap.sources.asgi_env_source_factory import (
    ASGIEnvSourceFactory,
)
from answer_service.setup.bootstrap.sources.logging_env_source_factory import (
    LoggingEnvSourceFactory,
)
from answer_service.setup.bootstrap.sources.postgres_env_source_factory import (
    PostgresEnvSourceFactory,
)
from tests.unit.factories.env_data_factories import (
    asgi_env,
    logging_env,
    postgres_env,
    sqlalchemy_env,
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
