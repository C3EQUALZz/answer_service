from typing import TYPE_CHECKING, Final, override

from dature import load

from answer_service.setup.bootstrap.loaders.loader import ConfigLoader
from answer_service.setup.configs.storage_config import StorageConfig

if TYPE_CHECKING:
    from answer_service.setup.bootstrap.sources.source_factory import SourceFactory


class StorageConfigLoader(ConfigLoader[StorageConfig]):
    """``dature``-backed loader for :class:`StorageConfig`."""

    def __init__(self, source_factory: SourceFactory) -> None:
        self._source_factory: Final[SourceFactory] = source_factory

    @override
    def load(self) -> StorageConfig:
        return load(self._source_factory.create(), schema=StorageConfig)
