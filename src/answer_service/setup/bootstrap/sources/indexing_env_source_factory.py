from typing import TYPE_CHECKING, override

from dature import EnvSource, F

from answer_service.setup.bootstrap.sources.source_factory import SourceFactory
from answer_service.setup.configs.indexing_config import IndexingConfig

if TYPE_CHECKING:
    from dature.sources.protocol import SourceProtocol


class IndexingEnvSourceFactory(SourceFactory):
    """Maps ``INDEXING_*`` environment variables onto :class:`IndexingConfig`."""

    @override
    def create(self) -> SourceProtocol:
        return EnvSource(
            field_mapping={
                F[IndexingConfig].stuck_after_seconds: "INDEXING_STUCK_AFTER_SECONDS",
            },
        )
