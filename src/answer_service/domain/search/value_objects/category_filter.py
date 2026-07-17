from dataclasses import dataclass
from typing import override

from answer_service.domain.common.value_object import ValueObject
from answer_service.domain.search.errors import EmptyCategoryFilterError


@dataclass(frozen=True, kw_only=True)
class CategoryFilter(ValueObject):
    """Optional category a search is restricted to."""

    value: str

    @override
    def _validate(self) -> None:
        if not self.value.strip():
            msg = "Category filter cannot be empty."
            raise EmptyCategoryFilterError(msg)

    def __str__(self) -> str:
        return self.value
