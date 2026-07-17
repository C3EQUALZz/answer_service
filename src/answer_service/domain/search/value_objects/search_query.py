from dataclasses import dataclass
from typing import override

from answer_service.domain.common.value_object import ValueObject
from answer_service.domain.search.errors import (
    EmptySearchQueryError,
    SearchQueryTooLongError,
)

MAX_QUERY_LENGTH: int = 1024


@dataclass(frozen=True, kw_only=True)
class SearchQuery(ValueObject):
    """The user's free-text query."""

    content: str

    @override
    def _validate(self) -> None:
        if not self.content.strip():
            msg = "Search query cannot be empty."
            raise EmptySearchQueryError(msg)
        if len(self.content) > MAX_QUERY_LENGTH:
            msg = f"Search query exceeds maximum length of {MAX_QUERY_LENGTH} characters."
            raise SearchQueryTooLongError(msg)

    def __str__(self) -> str:
        return self.content
