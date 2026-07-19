import logging
from typing import Final, override

from answer_service.application.common.mediator.handlers import QueryHandler
from answer_service.application.common.services import HybridSearchService
from answer_service.application.queries.search.search_qa_pairs.query import (
    SearchQAPairsQuery,
    SearchQAPairsResponse,
)

logger: Final[logging.Logger] = logging.getLogger(__name__)


class SearchQAPairsHandler(
    QueryHandler[SearchQAPairsQuery, SearchQAPairsResponse],
):
    """Returns the hybrid ranking for one set of criteria.

    Thin on purpose: retrieval and fusion live in ``HybridSearchService`` so
    ``/api/v1/ask`` can ground an answer in exactly the same ranking without going
    back through the mediator and being counted as a second served query.
    """

    def __init__(self, hybrid_search: HybridSearchService) -> None:
        self._hybrid_search: Final[HybridSearchService] = hybrid_search

    @override
    async def handle(self, query: SearchQAPairsQuery) -> SearchQAPairsResponse:
        logger.info(
            "search_qa_pairs: query '%s', top_k=%d, category=%s",
            query.criteria.query.content,
            query.criteria.top_k.value,
            query.criteria.category,
        )

        hits = await self._hybrid_search.search(query.criteria)
        response = SearchQAPairsResponse(query=query.criteria.query, hits=hits)

        logger.info(
            "search_qa_pairs: '%s' returned %d hit(s), top_score=%s",
            query.criteria.query.content,
            response.results_count,
            response.top_score,
        )
        for hit in hits:
            logger.debug(
                "search_qa_pairs: #%d '%s' final=%.4f dense=%s lexical=%s",
                hit.result.rank,
                hit.pair.external_id,
                hit.result.scores.final.value,
                hit.result.scores.dense,
                hit.result.scores.lexical,
            )

        return response
