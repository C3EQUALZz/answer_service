from dataclasses import dataclass
from typing import override

from answer_service.domain.common.value_object import ValueObject
from answer_service.domain.conversation.errors import EmptyAnswerError


@dataclass(frozen=True, kw_only=True)
class AnswerText(ValueObject):
    """The prose a model produced for one question."""

    content: str

    @override
    def _validate(self) -> None:
        if not self.content.strip():
            msg = "A generated answer cannot be empty."
            raise EmptyAnswerError(msg)

    def __str__(self) -> str:
        return self.content
