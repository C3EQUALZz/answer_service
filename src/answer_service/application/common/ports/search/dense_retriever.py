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


class DenseRetriever(Protocol):
    """Semantic half of hybrid search, backed by the vector store."""

    @abstractmethod
    async def retrieve(self, criteria: SearchCriteria) -> Sequence[ScoredCandidate]:
        """Returns candidates ordered by similarity, best first.

        Ordering is part of the contract: Reciprocal Rank Fusion consumes the
        position of each candidate, not its raw score, so an unordered result
        would silently corrupt the ranking.
        """
        raise NotImplementedError
