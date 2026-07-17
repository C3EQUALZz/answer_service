from typing import TYPE_CHECKING, Final, override

from dature import load

from answer_service.setup.bootstrap.loaders.loader import ConfigLoader
from answer_service.setup.configs.logging_config import LoggingConfig

if TYPE_CHECKING:
    from answer_service.setup.bootstrap.sources.source_factory import SourceFactory


class LoggingConfigLoader(ConfigLoader[LoggingConfig]):
    """``dature``-backed loader for :class:`LoggingConfig`.

    Backend-agnostic: the concrete :class:`SourceFactory` is injected in the DI
    container. The ``level`` field is validated by its ``Literal`` type, so no
    extra root validators are needed.
    """

    def __init__(self, source_factory: SourceFactory) -> None:
        self._source_factory: Final[SourceFactory] = source_factory

    @override
    def load(self) -> LoggingConfig:
        return load(
            self._source_factory.create(),
            schema=LoggingConfig,
        )
