from typing import TYPE_CHECKING

from answer_service.setup.configs.alchemy_config import SQLAlchemyConfig
from answer_service.setup.configs.asgi_config import ASGIConfig
from answer_service.setup.configs.logging_config import LogLevel, LoggingConfig
from answer_service.setup.configs.postgres_config import PostgresConfig

if TYPE_CHECKING:
    from pathlib import Path


def create_asgi_config(
    *,
    host: str = "127.0.0.1",
    port: int = 8080,
    fastapi_debug: bool = True,
    allow_credentials: bool = False,
) -> ASGIConfig:
    """Object mother for a valid :class:`ASGIConfig` (default CORS lists)."""
    return ASGIConfig(
        host=host,
        port=port,
        fastapi_debug=fastapi_debug,
        allow_credentials=allow_credentials,
    )


def create_postgres_config(
    *,
    user: str = "app",
    password: str = "s3cr3t",
    host: str = "localhost",
    port: int = 5432,
    db_name: str = "app_db",
    driver: str = "asyncpg",
) -> PostgresConfig:
    """Object mother for a valid :class:`PostgresConfig`."""
    return PostgresConfig(
        user=user,
        password=password,
        host=host,
        port=port,
        db_name=db_name,
        driver=driver,
    )


def create_sqlalchemy_config(
    *,
    pool_pre_ping: bool = True,
    pool_recycle: int = 30,
    pool_size: int = 10,
    max_overflow: int = 5,
    echo: bool = False,
    auto_flush: bool = False,
    expire_on_commit: bool = False,
    future: bool = True,
) -> SQLAlchemyConfig:
    """Object mother for a valid :class:`SQLAlchemyConfig`."""
    return SQLAlchemyConfig(
        pool_pre_ping=pool_pre_ping,
        pool_recycle=pool_recycle,
        pool_size=pool_size,
        max_overflow=max_overflow,
        echo=echo,
        auto_flush=auto_flush,
        expire_on_commit=expire_on_commit,
        future=future,
    )


def create_logging_config(
    *,
    render_json_logs: bool = False,
    log_path: Path | None = None,
    level: LogLevel = "INFO",
) -> LoggingConfig:
    """Object mother for a valid :class:`LoggingConfig`."""
    return LoggingConfig(
        render_json_logs=render_json_logs,
        log_path=log_path,
        level=level,
    )
