from dataclasses import dataclass
from typing import Final

HTTPS_SCHEME: Final[str] = "https"
HTTP_SCHEME: Final[str] = "http"


@dataclass(slots=True, frozen=True)
class QdrantConfig:
    """Connection and collection settings for the Qdrant vector store.

    Attributes:
        host: Qdrant server hostname or IP address.
        port: Qdrant HTTP port.
        api_key: API key, empty for an unsecured local instance.
        collection_name: Collection holding the QA pair vectors.
        use_https: Whether to talk to the server over TLS.
        prefer_grpc: Whether to use the gRPC transport, which is faster for
            bulk upserts during indexing.
        timeout_seconds: Ceiling on a single Qdrant request. Bounds both the
            dense search on the read path and the collection check at startup,
            so an unreachable Qdrant fails the request (or the boot) instead of
            hanging it.

    Properties:
        url: Complete Qdrant connection URL.
    """

    host: str
    port: int = 6333
    api_key: str = ""
    collection_name: str = "qa_pairs"
    use_https: bool = False
    prefer_grpc: bool = False
    timeout_seconds: int = 10

    @property
    def url(self) -> str:
        """Builds the Qdrant connection URL."""
        scheme = HTTPS_SCHEME if self.use_https else HTTP_SCHEME
        return f"{scheme}://{self.host}:{self.port}"
