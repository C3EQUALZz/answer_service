from dataclasses import dataclass
from typing import override

from answer_service.domain.common.value_object import ValueObject
from answer_service.domain.search.value_objects.score import Score


@dataclass(frozen=True, kw_only=True)
class Scores(ValueObject):
    """The score breakdown behind a ranked result.

    ``dense`` and ``lexical`` are the original per-retriever scores (``None``
    when the result was not found by that retriever); ``final`` is the fused
    score the ranking is ordered by.
    """

    final: Score
    dense: Score | None = None
    lexical: Score | None = None

    @override
    def _validate(self) -> None:
        """Component value objects validate themselves."""
