from dataclasses import dataclass
from typing import override

from answer_service.domain.analytics.errors import EmptyCategoryLabelError
from answer_service.domain.common.value_object import ValueObject


@dataclass(frozen=True, kw_only=True)
class CategoryLabel(ValueObject):
    """The category a query was restricted to, as recorded for reporting."""

    value: str

    @override
    def _validate(self) -> None:
        if not self.value.strip():
            msg = "Category label cannot be empty."
            raise EmptyCategoryLabelError(msg)

    def __str__(self) -> str:
        return self.value
