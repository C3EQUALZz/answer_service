from typing import TYPE_CHECKING, override

from dature import EnvSource, F

from answer_service.setup.bootstrap.sources.source_factory import SourceFactory
from answer_service.setup.configs.nats_config import NatsConfig

if TYPE_CHECKING:
    from dature.sources.protocol import SourceProtocol


class NatsEnvSourceFactory(SourceFactory):
    """Maps ``NATS_*`` environment variables onto :class:`NatsConfig`."""

    @override
    def create(self) -> SourceProtocol:
        return EnvSource(
            field_mapping={
                F[NatsConfig].host: "NATS_HOST",
                F[NatsConfig].port: "NATS_PORT",
                F[NatsConfig].user: "NATS_USER",
                F[NatsConfig].password: "NATS_PASSWORD",
            },
        )
