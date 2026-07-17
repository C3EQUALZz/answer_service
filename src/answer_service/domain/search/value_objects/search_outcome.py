from dataclasses import dataclass
from typing import override

from answer_service.domain.common.value_object import ValueObject
from answer_service.domain.search.value_objects.ranked_result import RankedResult
from answer_service.domain.search.value_objects.search_query import SearchQuery


@dataclass(frozen=True, kw_only=True)
class SearchOutcome(ValueObject):
    """The result of a hybrid search: the query and its ranked results.

    Request id and duration are cross-cutting concerns added by the application
    layer, not part of the search domain.
    """

    query: SearchQuery
    results: tuple[RankedResult, ...]

    @property
    def is_empty(self) -> bool:
        return not self.results

    @override
    def _validate(self) -> None:
        """Component value objects validate themselves."""
