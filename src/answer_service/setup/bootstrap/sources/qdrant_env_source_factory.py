from typing import TYPE_CHECKING, override

from dature import EnvSource, F

from answer_service.setup.bootstrap.sources.source_factory import SourceFactory
from answer_service.setup.configs.qdrant_config import QdrantConfig

if TYPE_CHECKING:
    from dature.sources.protocol import SourceProtocol


class QdrantEnvSourceFactory(SourceFactory):
    """Maps ``QDRANT_*`` environment variables onto :class:`QdrantConfig`."""

    @override
    def create(self) -> SourceProtocol:
        return EnvSource(
            field_mapping={
                F[QdrantConfig].host: "QDRANT_HOST",
                F[QdrantConfig].port: "QDRANT_PORT",
                F[QdrantConfig].api_key: "QDRANT_API_KEY",
                F[QdrantConfig].collection_name: "QDRANT_COLLECTION_NAME",
                F[QdrantConfig].use_https: "QDRANT_USE_HTTPS",
                F[QdrantConfig].prefer_grpc: "QDRANT_PREFER_GRPC",
            },
        )
