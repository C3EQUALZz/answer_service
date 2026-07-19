from dataclasses import dataclass

from answer_service.application.common.mediator.markers import Query
from answer_service.application.common.ports.gateways import QAPairView
from answer_service.domain.search.value_objects.ranked_result import RankedResult
from answer_service.domain.search.value_objects.search_criteria import SearchCriteria
from answer_service.domain.search.value_objects.search_query import SearchQuery


@dataclass(frozen=True, slots=True)
class SearchHit:
    """One ranked pair with the text a caller needs to read it."""

    result: RankedResult
    pair: QAPairView


@dataclass(frozen=True, slots=True)
class SearchQAPairsResponse:
    """The ranking, best first, with the query that produced it."""

    query: SearchQuery
    hits: tuple[SearchHit, ...]

    @property
    def is_empty(self) -> bool:
        return not self.hits

    @property
    def top_score(self) -> float | None:
        if not self.hits:
            return None
        return self.hits[0].result.scores.final.value


@dataclass(frozen=True, slots=True)
class SearchQAPairsQuery(Query[SearchQAPairsResponse]):
    """Finds the catalog entries that best answer a question.

    Both retrievers see the same criteria, including ``top_k``: each returns its
    own best ``top_k``, and fusion picks the final ``top_k`` from the union. A
    pair only one retriever found can therefore still win, which is the whole
    reason for running two.
    """

    criteria: SearchCriteria
