from dataclasses import dataclass
from typing import override

from answer_service.domain.common.value_object import ValueObject
from answer_service.domain.search.errors import TopKOutOfRangeError

MIN_TOP_K: int = 1
MAX_TOP_K: int = 20


@dataclass(frozen=True, kw_only=True)
class TopK(ValueObject):
    """How many results a search should return."""

    value: int

    @override
    def _validate(self) -> None:
        if not MIN_TOP_K <= self.value <= MAX_TOP_K:
            msg = f"top_k must be between {MIN_TOP_K} and {MAX_TOP_K}, got {self.value}."
            raise TopKOutOfRangeError(msg)
