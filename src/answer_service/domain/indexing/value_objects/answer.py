from dataclasses import dataclass
from typing import override

from answer_service.domain.common.value_object import ValueObject
from answer_service.domain.indexing.errors import AnswerTooLongError, EmptyAnswerError

MAX_ANSWER_LENGTH: int = 16384


@dataclass(frozen=True, kw_only=True)
class Answer(ValueObject):
    """The answer text of a QA pair."""

    content: str

    @override
    def _validate(self) -> None:
        if not self.content.strip():
            msg = "Answer content cannot be empty."
            raise EmptyAnswerError(msg)
        if len(self.content) > MAX_ANSWER_LENGTH:
            msg = f"Answer exceeds maximum length of {MAX_ANSWER_LENGTH} characters."
            raise AnswerTooLongError(msg)

    def __str__(self) -> str:
        return self.content
