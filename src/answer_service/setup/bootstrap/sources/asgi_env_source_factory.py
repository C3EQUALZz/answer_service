from typing import TYPE_CHECKING, override

from dature import EnvSource, F

from answer_service.setup.bootstrap.sources.source_factory import SourceFactory
from answer_service.setup.configs.asgi_config import ASGIConfig

if TYPE_CHECKING:
    from dature.sources.protocol import SourceProtocol


class ASGIEnvSourceFactory(SourceFactory):
    """Maps ``UVICORN_*`` / ``FASTAPI_*`` env vars onto :class:`ASGIConfig`."""

    @override
    def create(self) -> SourceProtocol:
        return EnvSource(
            field_mapping={
                F[ASGIConfig].host: "UVICORN_HOST",
                F[ASGIConfig].port: "UVICORN_PORT",
                F[ASGIConfig].fastapi_debug: "FASTAPI_DEBUG",
                F[ASGIConfig].allow_credentials: "FASTAPI_ALLOW_CREDENTIALS",
            },
        )
