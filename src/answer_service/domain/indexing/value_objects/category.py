from dataclasses import dataclass
from typing import override

from answer_service.domain.common.value_object import ValueObject
from answer_service.domain.indexing.errors import EmptyCategoryError


@dataclass(frozen=True, kw_only=True)
class Category(ValueObject):
    """Topic/category a QA pair belongs to."""

    value: str

    @override
    def _validate(self) -> None:
        if not self.value.strip():
            msg = "Category cannot be empty."
            raise EmptyCategoryError(msg)

    def __str__(self) -> str:
        return self.value
