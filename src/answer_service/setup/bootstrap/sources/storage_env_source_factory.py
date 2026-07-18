from typing import TYPE_CHECKING, override

from dature import EnvSource, F

from answer_service.setup.bootstrap.sources.source_factory import SourceFactory
from answer_service.setup.configs.storage_config import StorageConfig

if TYPE_CHECKING:
    from dature.sources.protocol import SourceProtocol


class StorageEnvSourceFactory(SourceFactory):
    """Maps ``SOURCE_STORAGE_*`` environment variables onto :class:`StorageConfig`."""

    @override
    def create(self) -> SourceProtocol:
        return EnvSource(
            field_mapping={
                F[StorageConfig].directory: "SOURCE_STORAGE_DIRECTORY",
            },
        )
