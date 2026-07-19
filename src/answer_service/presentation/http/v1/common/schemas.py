import time
from typing import Annotated

from pydantic import BaseModel, Field

from answer_service.domain.search.value_objects.category_filter import CategoryFilter
from answer_service.domain.search.value_objects.search_criteria import SearchCriteria
from answer_service.domain.search.value_objects.search_query import (
    MAX_QUERY_LENGTH,
    SearchQuery,
)
from answer_service.domain.search.value_objects.top_k import MAX_TOP_K, MIN_TOP_K, TopK

MILLISECONDS_PER_SECOND: int = 1000


def elapsed_ms(started_at: float) -> int:
    """How long the caller waited, for the ``duration_ms`` field.

    Separate from the latency the recording pipeline journals: that one measures
    the handler, this one measures the request, and only the second is what a
    caller can observe.
    """
    return round((time.perf_counter() - started_at) * MILLISECONDS_PER_SECOND)


class CriteriaRequest(BaseModel):
    """What every endpoint that consults the catalog accepts.

    Shared so ``/api/v1/search`` and ``/api/v1/ask`` cannot drift on what a valid query
    is — a question one of them rejects and the other accepts would make the two
    endpoints answer different catalogs.
    """

    query: Annotated[
        str,
        Field(
            min_length=1,
            max_length=MAX_QUERY_LENGTH,
            description="Free-text question to consult the catalog with",
        ),
    ]
    top_k: Annotated[
        int,
        Field(
            ge=MIN_TOP_K,
            le=MAX_TOP_K,
            description="How many catalog entries to draw on",
        ),
    ] = MIN_TOP_K
    category: Annotated[
        str | None,
        Field(description="Restrict the search to one category"),
    ] = None

    def to_criteria(self) -> SearchCriteria:
        return SearchCriteria(
            query=SearchQuery(content=self.query),
            top_k=TopK(value=self.top_k),
            category=(
                CategoryFilter(value=self.category) if self.category is not None else None
            ),
        )
