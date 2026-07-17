from dataclasses import dataclass
from typing import override

from answer_service.domain.common.value_object import ValueObject
from answer_service.domain.indexing.value_objects.external_id import ExternalId
from answer_service.domain.search.value_objects.score import Score


@dataclass(frozen=True, kw_only=True)
class ScoredCandidate(ValueObject):
    """A single hit returned by one retriever (dense or lexical).

    Candidates are assumed to be delivered by each retriever already ordered by
    ``score`` descending; their position feeds Reciprocal Rank Fusion.
    """

    external_id: ExternalId
    score: Score

    @override
    def _validate(self) -> None:
        """Component value objects validate themselves."""
