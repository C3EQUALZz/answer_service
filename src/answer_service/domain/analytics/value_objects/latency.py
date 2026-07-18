from dataclasses import dataclass
from typing import override

from answer_service.domain.analytics.errors import NegativeLatencyError
from answer_service.domain.common.value_object import ValueObject


@dataclass(frozen=True, kw_only=True)
class Latency(ValueObject):
    """How long a request took, in milliseconds."""

    milliseconds: int

    @override
    def _validate(self) -> None:
        if self.milliseconds < 0:
            msg = f"Latency cannot be negative, got {self.milliseconds}."
            raise NegativeLatencyError(msg)
