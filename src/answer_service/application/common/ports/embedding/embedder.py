from abc import abstractmethod
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Sequence


class Embedder(Protocol):
    """Turns text into the dense vectors the search index is built on."""

    @abstractmethod
    async def embed_query(self, text: str) -> list[float]:
        """Embeds a search query.

        Separate from :meth:`embed_documents` because some models prepend a
        different instruction prefix to queries than to documents, and mixing
        the two silently degrades recall.
        """
        raise NotImplementedError

    @abstractmethod
    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Embeds documents in one call, preserving order.

        ``result[i]`` corresponds to ``texts[i]``.
        """
        raise NotImplementedError
