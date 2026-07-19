import asyncio
import logging
from typing import Final, override

from answer_service.application.common.mediator.handlers import QueryHandler
from answer_service.application.common.ports.gateways import QACatalogQueryGateway
from answer_service.application.common.ports.search import (
    DenseRetriever,
    LexicalRetriever,
)
from answer_service.application.queries.search.search_qa_pairs.query import (
    SearchHit,
    SearchQAPairsQuery,
    SearchQAPairsResponse,
)
from answer_service.domain.search.services.rrf_fusion import RrfFusion

logger: Final[logging.Logger] = logging.getLogger(__name__)


class SearchQAPairsHandler(
    QueryHandler[SearchQAPairsQuery, SearchQAPairsResponse],
):
    """Runs both retrievers, fuses their rankings and joins the text.

    The two retrievers are independent and neither is fast, so they run
    concurrently: the request costs the slower of the two rather than their sum.

    They also disagree about what exists. The lexical side reads the catalog
    directly and sees a pair as soon as it is committed; the dense side only
    sees it once the outbox has been relayed and projected. A pair the vector
    store has not caught up on is therefore still findable, and one the catalog
    has already deleted is dropped when the text is joined.
    """

    def __init__(
        self,
        dense_retriever: DenseRetriever,
        lexical_retriever: LexicalRetriever,
        rrf_fusion: RrfFusion,
        catalog: QACatalogQueryGateway,
    ) -> None:
        self._dense_retriever: Final[DenseRetriever] = dense_retriever
        self._lexical_retriever: Final[LexicalRetriever] = lexical_retriever
        self._rrf_fusion: Final[RrfFusion] = rrf_fusion
        self._catalog: Final[QACatalogQueryGateway] = catalog

    @override
    async def handle(self, query: SearchQAPairsQuery) -> SearchQAPairsResponse:
        dense, lexical = await asyncio.gather(
            self._dense_retriever.retrieve(query.criteria),
            self._lexical_retriever.retrieve(query.criteria),
        )

        ranked = self._rrf_fusion.fuse(
            dense=dense,
            lexical=lexical,
            top_k=query.criteria.top_k,
        )

        views = await self._catalog.read_views(
            result.external_id for result in ranked
        )

        return SearchQAPairsResponse(
            query=query.criteria.query,
            hits=tuple(
                SearchHit(result=result, pair=views[result.external_id])
                for result in ranked
                if result.external_id in views
            ),
        )
