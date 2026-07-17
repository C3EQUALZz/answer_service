from dataclasses import dataclass
from typing import override

from answer_service.domain.common.value_object import ValueObject
from answer_service.domain.indexing.value_objects.external_id import ExternalId
from answer_service.domain.search.errors import InvalidRankError
from answer_service.domain.search.value_objects.result_scores import Scores

MIN_RANK: int = 1


@dataclass(frozen=True, kw_only=True)
class RankedResult(ValueObject):
    """A QA pair at a definite position in the final ranking.

    Carries only the shared identity (``external_id``) and the scores; the
    question/answer text is joined from the catalog by the application layer.
    """

    external_id: ExternalId
    rank: int
    scores: Scores

    @override
    def _validate(self) -> None:
        if self.rank < MIN_RANK:
            msg = f"rank must be >= {MIN_RANK}, got {self.rank}."
            raise InvalidRankError(msg)
