import logging
from typing import TYPE_CHECKING, Final, final, override

from langchain_core.embeddings import Embeddings

from answer_service.application.common.ports.embedding import Embedder

if TYPE_CHECKING:
    from collections.abc import Sequence


logger: Final[logging.Logger] = logging.getLogger(__name__)


@final
class LangChainEmbedder(Embedder):
    """Embedder backed by any LangChain ``Embeddings`` implementation.

    Depends on the LangChain interface rather than on Mistral directly, so
    swapping the provider is a wiring change in the container and touches no
    adapter code.
    """

    def __init__(self, embeddings: Embeddings) -> None:
        self._embeddings: Final[Embeddings] = embeddings

    @override
    async def embed_query(self, text: str) -> list[float]:
        logger.debug("embedder: embedding a query of %d character(s)", len(text))
        vector = await self._embeddings.aembed_query(text)
        logger.debug("embedder: query vector has %d dimension(s)", len(vector))
        return vector

    @override
    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            logger.debug("embedder: nothing to embed")
            return []

        logger.info("embedder: embedding %d document(s)", len(texts))
        vectors = await self._embeddings.aembed_documents(list(texts))
        logger.info("embedder: embedded %d document(s)", len(vectors))
        return vectors
