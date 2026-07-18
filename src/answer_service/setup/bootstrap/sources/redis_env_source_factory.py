from typing import TYPE_CHECKING, override

from dature import EnvSource, F

from answer_service.setup.bootstrap.sources.source_factory import SourceFactory
from answer_service.setup.configs.redis_config import RedisConfig

if TYPE_CHECKING:
    from dature.sources.protocol import SourceProtocol


class RedisEnvSourceFactory(SourceFactory):
    """Maps ``REDIS_*`` environment variables onto :class:`RedisConfig`."""

    @override
    def create(self) -> SourceProtocol:
        return EnvSource(
            field_mapping={
                F[RedisConfig].host: "REDIS_HOST",
                F[RedisConfig].port: "REDIS_PORT",
                F[RedisConfig].password: "REDIS_PASSWORD",
                F[RedisConfig].worker_db: "REDIS_WORKER_DB",
                F[RedisConfig].schedule_source_db: "REDIS_SCHEDULE_SOURCE_DB",
                F[RedisConfig].cache_db: "REDIS_CACHE_DB",
            },
        )
