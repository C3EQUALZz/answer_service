from dataclasses import dataclass
from typing import Any

from taskiq import AsyncBroker

from answer_service.setup.bootstrap.loaders.alchemy_config_loader import (
    SQLAlchemyConfigLoader,
)
from answer_service.setup.bootstrap.loaders.asgi_config_loader import ASGIConfigLoader
from answer_service.setup.bootstrap.loaders.logging_config_loader import (
    LoggingConfigLoader,
)
from answer_service.setup.bootstrap.loaders.mistral_config_loader import (
    MistralConfigLoader,
)
from answer_service.setup.bootstrap.loaders.nats_config_loader import NatsConfigLoader
from answer_service.setup.bootstrap.loaders.postgres_config_loader import (
    PostgresConfigLoader,
)
from answer_service.setup.bootstrap.loaders.qdrant_config_loader import (
    QdrantConfigLoader,
)
from answer_service.setup.bootstrap.loaders.redis_config_loader import RedisConfigLoader
from answer_service.setup.bootstrap.loaders.search_config_loader import (
    SearchConfigLoader,
)
from answer_service.setup.bootstrap.loaders.storage_config_loader import (
    StorageConfigLoader,
)
from answer_service.setup.bootstrap.loaders.taskiq_config_loader import (
    TaskIQConfigLoader,
)
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
from answer_service.setup.bootstrap.sources.search_env_source_factory import (
    SearchEnvSourceFactory,
)
from answer_service.setup.bootstrap.sources.storage_env_source_factory import (
    StorageEnvSourceFactory,
)
from answer_service.setup.bootstrap.sources.taskiq_env_source_factory import (
    TaskIQEnvSourceFactory,
)
from answer_service.setup.configs.alchemy_config import SQLAlchemyConfig
from answer_service.setup.configs.asgi_config import ASGIConfig
from answer_service.setup.configs.logging_config import LoggingConfig
from answer_service.setup.configs.mistral_config import MistralConfig
from answer_service.setup.configs.nats_config import NatsConfig
from answer_service.setup.configs.postgres_config import PostgresConfig
from answer_service.setup.configs.qdrant_config import QdrantConfig
from answer_service.setup.configs.redis_config import RedisConfig
from answer_service.setup.configs.search_config import SearchConfig
from answer_service.setup.configs.storage_config import StorageConfig
from answer_service.setup.configs.taskiq_config import TaskIQConfig


@dataclass(slots=True, frozen=True)
class AppConfigs:
    """Every configuration the process needs, loaded once at startup."""

    asgi: ASGIConfig
    logging: LoggingConfig
    postgres: PostgresConfig
    alchemy: SQLAlchemyConfig
    nats: NatsConfig
    redis: RedisConfig
    taskiq: TaskIQConfig
    mistral: MistralConfig
    qdrant: QdrantConfig
    search: SearchConfig
    storage: StorageConfig


def setup_configs() -> AppConfigs:
    """Loads every config from the environment.

    All of them, eagerly, at startup: a service that boots and only discovers a
    missing variable when the first request touches that subsystem is far worse
    to operate than one that refuses to start.

    Which source each loader reads from is a wiring decision made here — swap
    the factories and the same configs come from TOML, YAML or Vault without
    touching a loader.
    """
    return AppConfigs(
        asgi=ASGIConfigLoader(ASGIEnvSourceFactory()).load(),
        logging=LoggingConfigLoader(LoggingEnvSourceFactory()).load(),
        postgres=PostgresConfigLoader(PostgresEnvSourceFactory()).load(),
        alchemy=SQLAlchemyConfigLoader(SQLAlchemyEnvSourceFactory()).load(),
        nats=NatsConfigLoader(NatsEnvSourceFactory()).load(),
        redis=RedisConfigLoader(RedisEnvSourceFactory()).load(),
        taskiq=TaskIQConfigLoader(TaskIQEnvSourceFactory()).load(),
        mistral=MistralConfigLoader(MistralEnvSourceFactory()).load(),
        qdrant=QdrantConfigLoader(QdrantEnvSourceFactory()).load(),
        search=SearchConfigLoader(SearchEnvSourceFactory()).load(),
        storage=StorageConfigLoader(StorageEnvSourceFactory()).load(),
    )


def make_container_context(
    configs: AppConfigs,
    broker: AsyncBroker,
) -> dict[type, Any]:
    """Builds the context the container is created with.

    Keyed by the type each object is provided as, matching the
    ``from_context`` declarations in ``configs_provider``. Kept here so the
    three entry points cannot drift apart on what they pass in.
    """
    return {
        ASGIConfig: configs.asgi,
        PostgresConfig: configs.postgres,
        SQLAlchemyConfig: configs.alchemy,
        NatsConfig: configs.nats,
        RedisConfig: configs.redis,
        TaskIQConfig: configs.taskiq,
        MistralConfig: configs.mistral,
        QdrantConfig: configs.qdrant,
        SearchConfig: configs.search,
        StorageConfig: configs.storage,
        AsyncBroker: broker,
    }
