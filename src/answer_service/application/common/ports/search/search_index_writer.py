from abc import abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from answer_service.domain.indexing.value_objects.external_id import ExternalId

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass(frozen=True, slots=True)
class IndexDocument:
    """A QA pair as handed to the search stores.

    Carries only text; computing the dense embedding is an implementation detail
    of the writer (which owns the embedding model), so the application never
    deals with vectors.
    """

    external_id: ExternalId
    question: str
    answer: str
    category: str


class SearchIndexWriter(Protocol):
    """Keeps the dense (Qdrant) and lexical (PostgreSQL FTS) stores in sync."""

    @abstractmethod
    async def upsert(self, documents: Sequence[IndexDocument]) -> None:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, external_ids: Sequence[ExternalId]) -> None:
        raise NotImplementedError
