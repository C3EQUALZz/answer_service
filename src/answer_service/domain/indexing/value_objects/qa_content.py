from dataclasses import dataclass
from typing import override

from answer_service.domain.common.value_object import ValueObject
from answer_service.domain.indexing.value_objects.answer import Answer
from answer_service.domain.indexing.value_objects.category import Category
from answer_service.domain.indexing.value_objects.content_hash import ContentHash
from answer_service.domain.indexing.value_objects.question import Question


@dataclass(frozen=True, kw_only=True)
class QAContent(ValueObject):
    """The change-tracked payload of a QA pair.

    Groups the fields that are versioned and fingerprinted together, so change
    detection is a plain value comparison and the search fingerprint has a
    single source of truth.
    """

    question: Question
    answer: Answer
    category: Category

    @property
    def fingerprint(self) -> ContentHash:
        return ContentHash.of(
            question=self.question,
            answer=self.answer,
            category=self.category,
        )

    @override
    def _validate(self) -> None:
        """Field value objects validate themselves; nothing extra here."""
