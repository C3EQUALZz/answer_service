from dataclasses import dataclass
from typing import override

from answer_service.application.common.analytics import RecordableQuery
from answer_service.application.common.services import SearchHit
from answer_service.domain.analytics.value_objects.query_kind import QueryKind
from answer_service.domain.search.value_objects.search_criteria import SearchCriteria
from answer_service.domain.search.value_objects.search_query import SearchQuery


@dataclass(frozen=True, slots=True)
class SearchQAPairsResponse:
    """The ranking, best first, with the query that produced it."""

    query: SearchQuery
    hits: tuple[SearchHit, ...]

    @property
    def is_empty(self) -> bool:
        return not self.hits

    @property
    def results_count(self) -> int:
        return len(self.hits)

    @property
    def top_score(self) -> float | None:
        if not self.hits:
            return None
        return self.hits[0].result.scores.final.value


@dataclass(frozen=True)
class SearchQAPairsQuery(RecordableQuery[SearchQAPairsResponse]):
    """Finds the catalog entries that best answer a question.

    Both retrievers see the same criteria, including ``top_k``: each returns its
    own best ``top_k``, and fusion picks the final ``top_k`` from the union. A
    pair only one retriever found can therefore still win, which is the whole
    reason for running two.
    """

    criteria: SearchCriteria

    @property
    @override
    def journalled_text(self) -> str:
        return self.criteria.query.content

    @property
    @override
    def journalled_kind(self) -> QueryKind:
        return QueryKind.SEARCH

    @property
    @override
    def journalled_category(self) -> str | None:
        if self.criteria.category is None:
            return None
        return self.criteria.category.value
