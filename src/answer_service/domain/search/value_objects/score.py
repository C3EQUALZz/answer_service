import math
from dataclasses import dataclass
from typing import override

from answer_service.domain.common.value_object import ValueObject
from answer_service.domain.search.errors import InvalidScoreError


@dataclass(frozen=True, kw_only=True)
class Score(ValueObject):
    """A single relevance score produced at some ranking stage."""

    value: float

    @override
    def _validate(self) -> None:
        if not math.isfinite(self.value):
            msg = f"Score must be a finite number, got {self.value}."
            raise InvalidScoreError(msg)
