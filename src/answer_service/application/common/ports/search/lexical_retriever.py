from abc import abstractmethod
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Sequence

    from answer_service.domain.search.value_objects.scored_candidate import (
        ScoredCandidate,
    )
    from answer_service.domain.search.value_objects.search_criteria import (
        SearchCriteria,
    )


class LexicalRetriever(Protocol):
    """Keyword half of hybrid search, backed by the relational store.

    Exists because the dense retriever is bad at exactly what a FAQ needs most:
    product names, error codes and other rare tokens that carry the meaning but
    barely move a sentence embedding.
    """

    @abstractmethod
    async def retrieve(self, criteria: SearchCriteria) -> Sequence[ScoredCandidate]:
        """Returns candidates ordered by lexical relevance, best first.

        Ordering is part of the contract for the same reason it is on the dense
        side: Reciprocal Rank Fusion reads positions, not scores, so an
        unordered result would corrupt the ranking without failing.
        """
        raise NotImplementedError
