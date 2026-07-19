import asyncio
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from answer_service.application.common.ports.gateways import (
    QACatalogQueryGateway,
    QAPairView,
)
from answer_service.application.common.ports.search import (
    DenseRetriever,
    LexicalRetriever,
)
from answer_service.domain.search.services.rrf_fusion import RrfFusion
from answer_service.domain.search.value_objects.ranked_result import RankedResult

if TYPE_CHECKING:
    from answer_service.domain.search.value_objects.search_criteria import SearchCriteria

logger: Final[logging.Logger] = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SearchHit:
    """One ranked pair with the text a caller needs to read it."""

    result: RankedResult
    pair: QAPairView


class HybridSearchService:
    """Retrieves from both sides, fuses the rankings and joins the text.

    Lives here rather than inside a query handler because two use cases need the
    same answer: ``/v1/search`` returns the ranking, ``/v1/ask`` grounds a
    generated answer in it. Sharing the service is what stops the two from ever
    disagreeing about what the catalog holds — a handler calling another handler
    would do the same thing, but by going back through the mediator it would be
    journalled twice and counted as two served queries.

    The two retrievers are independent and neither is fast, so they run
    concurrently: the search costs the slower of the two rather than their sum.

    They also disagree about what exists, on purpose. The lexical side reads the
    catalog directly and sees a pair as soon as it is committed; the dense side
    only sees it once the outbox has been relayed and projected. A pair the
    vector store has not caught up on is therefore still findable, and one the
    catalog has already deleted is dropped when the text is joined.
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

    async def search(self, criteria: SearchCriteria) -> tuple[SearchHit, ...]:
        dense, lexical = await asyncio.gather(
            self._dense_retriever.retrieve(criteria),
            self._lexical_retriever.retrieve(criteria),
        )
        logger.info(
            "hybrid_search: '%s' -> dense=%d lexical=%d candidate(s)",
            criteria.query.content,
            len(dense),
            len(lexical),
        )

        ranked = self._rrf_fusion.fuse(
            dense=dense,
            lexical=lexical,
            top_k=criteria.top_k,
        )
        logger.info("hybrid_search: fused into %d result(s)", len(ranked))

        views = await self._catalog.read_views(result.external_id for result in ranked)
        missing = [r.external_id for r in ranked if r.external_id not in views]
        if missing:
            logger.warning(
                "hybrid_search: dropping %d ranked pair(s) the catalog lost: %s",
                len(missing),
                missing,
            )

        return tuple(
            SearchHit(result=result, pair=views[result.external_id])
            for result in ranked
            if result.external_id in views
        )
