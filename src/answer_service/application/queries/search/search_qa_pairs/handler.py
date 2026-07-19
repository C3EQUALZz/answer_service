from typing import Final, override

from answer_service.application.common.mediator.handlers import QueryHandler
from answer_service.application.common.services import HybridSearchService
from answer_service.application.queries.search.search_qa_pairs.query import (
    SearchQAPairsQuery,
    SearchQAPairsResponse,
)


class SearchQAPairsHandler(
    QueryHandler[SearchQAPairsQuery, SearchQAPairsResponse],
):
    """Returns the hybrid ranking for one set of criteria.

    Thin on purpose: retrieval and fusion live in ``HybridSearchService`` so
    ``/v1/ask`` can ground an answer in exactly the same ranking without going
    back through the mediator and being counted as a second served query.
    """

    def __init__(self, hybrid_search: HybridSearchService) -> None:
        self._hybrid_search: Final[HybridSearchService] = hybrid_search

    @override
    async def handle(self, query: SearchQAPairsQuery) -> SearchQAPairsResponse:
        return SearchQAPairsResponse(
            query=query.criteria.query,
            hits=await self._hybrid_search.search(query.criteria),
        )
