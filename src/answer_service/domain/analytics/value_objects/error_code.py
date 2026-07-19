from dataclasses import dataclass
from typing import override

from answer_service.domain.analytics.errors import EmptyErrorCodeError
from answer_service.domain.common.value_object import ValueObject


@dataclass(frozen=True, kw_only=True)
class ErrorCode(ValueObject):
    """What went wrong, as a stable symbol rather than a sentence.

    A code, not a message: the report groups failures by it, and a message
    carrying an id or a table name would split one recurring fault into as many
    rows as it had occurrences.
    """

    value: str

    @override
    def _validate(self) -> None:
        if not self.value.strip():
            msg = "Error code cannot be empty."
            raise EmptyErrorCodeError(msg)

    def __str__(self) -> str:
        return self.value
