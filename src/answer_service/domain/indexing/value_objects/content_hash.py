import hashlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Self, override

from answer_service.domain.common.value_object import ValueObject
from answer_service.domain.indexing.errors import InvalidContentHashError

if TYPE_CHECKING:
    from answer_service.domain.indexing.value_objects.answer import Answer
    from answer_service.domain.indexing.value_objects.category import Category
    from answer_service.domain.indexing.value_objects.question import Question

_SHA256_HEX_LENGTH: int = 64
_FIELD_SEPARATOR: str = "\x1f"  # ASCII unit separator, cannot appear in text


@dataclass(frozen=True, kw_only=True)
class ContentHash(ValueObject):
    """Fingerprint of a QA pair's content.

    Drives idempotent synchronization: a pair is considered *changed* only when
    its content hash differs from the one already stored, regardless of the
    source ``updated_at`` timestamp.
    """

    value: str

    @classmethod
    def of(cls, *, question: Question, answer: Answer, category: Category) -> Self:
        payload = _FIELD_SEPARATOR.join(
            (question.content, answer.content, category.value),
        )
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return cls(value=digest)

    @override
    def _validate(self) -> None:
        if len(self.value) != _SHA256_HEX_LENGTH:
            msg = f"content hash must be a {_SHA256_HEX_LENGTH}-char sha256 digest."
            raise InvalidContentHashError(msg)

    def __str__(self) -> str:
        return self.value
