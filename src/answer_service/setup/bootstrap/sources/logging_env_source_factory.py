from typing import TYPE_CHECKING, override

from dature import EnvSource, F

from answer_service.setup.bootstrap.sources.source_factory import SourceFactory
from answer_service.setup.configs.logging_config import LoggingConfig

if TYPE_CHECKING:
    from dature.sources.protocol import SourceProtocol


class LoggingEnvSourceFactory(SourceFactory):
    """Maps logging environment variables onto :class:`LoggingConfig`."""

    @override
    def create(self) -> SourceProtocol:
        return EnvSource(
            field_mapping={
                F[LoggingConfig].render_json_logs: "RENDER_JSON_LOGS",
                F[LoggingConfig].log_path: "PATH_TO_SAVE_LOGS",
                F[LoggingConfig].level: "LOG_LEVEL",
            },
        )
