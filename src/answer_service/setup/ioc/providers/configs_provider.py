from typing import Final

from dishka import Provider, Scope
from taskiq import AsyncBroker

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


def configs_provider() -> Provider:
    """Supplies every configuration object from the container context.

    Configs are built once at startup by their loaders and handed to the
    container, rather than loaded here: reading the environment is a bootstrap
    decision, and a container that read it itself could not be built for a test.

    The broker arrives the same way — the worker entry point creates it before
    the container exists, since registering tasks is what makes it usable.
    """
    provider: Final[Provider] = Provider(scope=Scope.APP)
    provider.from_context(provides=ASGIConfig)
    provider.from_context(provides=PostgresConfig)
    provider.from_context(provides=SQLAlchemyConfig)
    provider.from_context(provides=NatsConfig)
    provider.from_context(provides=RedisConfig)
    provider.from_context(provides=TaskIQConfig)
    provider.from_context(provides=MistralConfig)
    provider.from_context(provides=QdrantConfig)
    provider.from_context(provides=IndexingConfig)
    provider.from_context(provides=SearchConfig)
    provider.from_context(provides=StorageConfig)
    provider.from_context(provides=AsyncBroker)
    return provider
