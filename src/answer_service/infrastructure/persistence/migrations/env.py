import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import Connection, pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from answer_service.infrastructure.persistence.models.base import metadata
from answer_service.setup.bootstrap.loaders.postgres_config_loader import (
    PostgresConfigLoader,
)
from answer_service.setup.bootstrap.setups.database_setup import setup_map_tables
from answer_service.setup.bootstrap.sources.postgres_env_source_factory import (
    PostgresEnvSourceFactory,
)

setup_map_tables()

config = context.config

postgres_config = PostgresConfigLoader(PostgresEnvSourceFactory()).load()
config.set_main_option("sqlalchemy.url", postgres_config.uri)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = metadata


def run_migrations_offline() -> None:
    """Emits the migration SQL against a URL, without connecting."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Runs the migrations over a real async connection.

    The driver is asyncpg, so alembic — which is synchronous — drives it through
    ``run_sync`` on an async engine. SQLAlchemy's ``async_fallback`` shortcut is
    not an option here: it calls ``asyncio.get_event_loop()``, which raises on
    Python 3.12+ when no loop is running.
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_async_migrations())
