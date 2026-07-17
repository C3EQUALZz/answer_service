from dataclasses import dataclass
from typing import override

from answer_service.domain.common.value_object import ValueObject
from answer_service.domain.indexing.errors import EmptyFailureCodeError


@dataclass(frozen=True, kw_only=True)
class FailureInfo(ValueObject):
    """Structured reason an indexing task ended unsuccessfully."""

    code: str
    message: str

    @override
    def _validate(self) -> None:
        if not self.code.strip():
            msg = "failure code cannot be empty."
            raise EmptyFailureCodeError(msg)

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"
