from typing import TYPE_CHECKING, override

from dature import EnvSource, F

from answer_service.setup.bootstrap.sources.source_factory import SourceFactory
from answer_service.setup.configs.postgres_config import PostgresConfig

if TYPE_CHECKING:
    from dature.sources.protocol import SourceProtocol


class PostgresEnvSourceFactory(SourceFactory):
    """Maps ``POSTGRES_*`` environment variables onto :class:`PostgresConfig`."""

    @override
    def create(self) -> SourceProtocol:
        return EnvSource(
            field_mapping={
                F[PostgresConfig].user: "POSTGRES_USER",
                F[PostgresConfig].password: "POSTGRES_PASSWORD",
                F[PostgresConfig].host: "POSTGRES_HOST",
                F[PostgresConfig].port: "POSTGRES_PORT",
                F[PostgresConfig].db_name: "POSTGRES_DB",
                F[PostgresConfig].driver: "POSTGRES_DRIVER",
            },
        )
