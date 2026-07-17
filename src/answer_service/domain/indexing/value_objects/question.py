from dataclasses import dataclass
from typing import override

from answer_service.domain.common.value_object import ValueObject
from answer_service.domain.indexing.errors import (
    EmptyQuestionError,
    QuestionTooLongError,
)

MAX_QUESTION_LENGTH: int = 4096


@dataclass(frozen=True, kw_only=True)
class Question(ValueObject):
    """The question text of a QA pair."""

    content: str

    @override
    def _validate(self) -> None:
        if not self.content.strip():
            msg = "Question content cannot be empty."
            raise EmptyQuestionError(msg)
        if len(self.content) > MAX_QUESTION_LENGTH:
            msg = f"Question exceeds maximum length of {MAX_QUESTION_LENGTH} characters."
            raise QuestionTooLongError(msg)

    def __str__(self) -> str:
        return self.content
