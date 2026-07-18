from typing import TYPE_CHECKING, Final, final, override

from langchain_core.embeddings import Embeddings

from answer_service.application.common.ports.embedding import Embedder

if TYPE_CHECKING:
    from collections.abc import Sequence


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
        return await self._embeddings.aembed_query(text)

    @override
    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        return await self._embeddings.aembed_documents(list(texts))
