from dataclasses import dataclass
from typing import override

from answer_service.domain.common.value_object import ValueObject
from answer_service.domain.search.value_objects.category_filter import CategoryFilter
from answer_service.domain.search.value_objects.search_query import SearchQuery
from answer_service.domain.search.value_objects.top_k import TopK


@dataclass(frozen=True, kw_only=True)
class SearchCriteria(ValueObject):
    """A fully-validated search request: what to look for and how much."""

    query: SearchQuery
    top_k: TopK
    category: CategoryFilter | None = None

    @override
    def _validate(self) -> None:
        """Component value objects validate themselves."""
