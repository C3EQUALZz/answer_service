from dataclasses import dataclass
from typing import override

from answer_service.domain.analytics.errors import (
    EmptyQueryTextError,
    QueryTextTooLongError,
)
from answer_service.domain.common.value_object import ValueObject

MAX_QUERY_TEXT_LENGTH: int = 1024


@dataclass(frozen=True, kw_only=True)
class QueryText(ValueObject):
    """The text a user searched for, as recorded for reporting.

    Deliberately its own value object rather than the search context's
    ``SearchQuery``: analytics keeps the text long after the search is over, and
    must not break when the search context changes what it accepts.
    """

    content: str

    @override
    def _validate(self) -> None:
        if not self.content.strip():
            msg = "Logged query text cannot be empty."
            raise EmptyQueryTextError(msg)
        if len(self.content) > MAX_QUERY_TEXT_LENGTH:
            msg = (
                f"Logged query text exceeds maximum length of "
                f"{MAX_QUERY_TEXT_LENGTH} characters."
            )
            raise QueryTextTooLongError(msg)

    def __str__(self) -> str:
        return self.content
