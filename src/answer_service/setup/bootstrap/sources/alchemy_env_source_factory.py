from typing import TYPE_CHECKING, override

from dature import EnvSource, F

from answer_service.setup.bootstrap.sources.source_factory import SourceFactory
from answer_service.setup.configs.alchemy_config import SQLAlchemyConfig

if TYPE_CHECKING:
    from dature.sources.protocol import SourceProtocol


class SQLAlchemyEnvSourceFactory(SourceFactory):
    """Maps ``DB_*`` environment variables onto :class:`SQLAlchemyConfig`."""

    @override
    def create(self) -> SourceProtocol:
        return EnvSource(
            field_mapping={
                F[SQLAlchemyConfig].pool_pre_ping: "DB_POOL_PRE_PING",
                F[SQLAlchemyConfig].pool_recycle: "DB_POOL_RECYCLE",
                F[SQLAlchemyConfig].pool_size: "DB_POOL_SIZE",
                F[SQLAlchemyConfig].max_overflow: "DB_POOL_MAX_OVERFLOW",
                F[SQLAlchemyConfig].echo: "DB_ECHO",
                F[SQLAlchemyConfig].auto_flush: "DB_AUTO_FLUSH",
                F[SQLAlchemyConfig].expire_on_commit: "DB_EXPIRE_ON_COMMIT",
                F[SQLAlchemyConfig].future: "DB_FUTURE",
            },
        )
