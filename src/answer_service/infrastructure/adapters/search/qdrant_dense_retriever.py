import logging
from typing import TYPE_CHECKING, Final, final, override

from langchain_qdrant import QdrantVectorStore
from qdrant_client import models

from answer_service.application.common.ports.search import DenseRetriever
from answer_service.domain.indexing.value_objects.external_id import ExternalId
from answer_service.domain.search.value_objects.score import Score
from answer_service.domain.search.value_objects.scored_candidate import ScoredCandidate
from answer_service.infrastructure.errors import SearchIndexError
from answer_service.setup.configs.search_config import SearchConfig

if TYPE_CHECKING:
    from collections.abc import Sequence

    from langchain_core.documents import Document

    from answer_service.domain.search.value_objects.search_criteria import SearchCriteria

logger: Final[logging.Logger] = logging.getLogger(__name__)

CATEGORY_PAYLOAD_KEY: Final[str] = "metadata.category"
EXTERNAL_ID_METADATA_KEY: Final[str] = "external_id"


@final
class QdrantDenseRetriever(DenseRetriever):
    """Semantic retrieval over the Qdrant collection.

    The query is embedded by the vector store with the same model that produced
    the indexed vectors — sharing one configured store is what guarantees the
    two never drift apart.

    Candidates below the configured similarity floor are dropped by Qdrant
    itself. Nearest-neighbour search always returns neighbours, however distant,
    so without a floor a question the catalog cannot answer comes back looking
    answered — and the gap report, which counts queries that found nothing,
    never counts anything.
    """

    def __init__(
        self,
        vector_store: QdrantVectorStore,
        search_config: SearchConfig,
    ) -> None:
        self._vector_store: Final[QdrantVectorStore] = vector_store
        self._score_floor: Final[float] = search_config.dense_score_floor

    @override
    async def retrieve(self, criteria: SearchCriteria) -> Sequence[ScoredCandidate]:
        logger.debug(
            "qdrant_dense: searching '%s', k=%d, floor=%.3f, category=%s",
            criteria.query.content,
            criteria.top_k.value,
            self._score_floor,
            criteria.category,
        )

        try:
            hits: list[
                tuple[Document, float]
            ] = await self._vector_store.asimilarity_search_with_score(
                query=criteria.query.content,
                k=criteria.top_k.value,
                filter=self._category_filter(criteria),
                score_threshold=self._score_floor,
            )
        except Exception as e:
            logger.exception("qdrant_dense: search failed")
            msg = "Failed to query Qdrant for dense candidates."
            raise SearchIndexError(msg) from e

        logger.info(
            "qdrant_dense: %d candidate(s) above floor %.3f",
            len(hits),
            self._score_floor,
        )
        for document, score in hits:
            logger.debug(
                "qdrant_dense: '%s' scored %.4f",
                document.metadata[EXTERNAL_ID_METADATA_KEY],
                score,
            )

        return [
            ScoredCandidate(
                external_id=ExternalId(
                    value=document.metadata[EXTERNAL_ID_METADATA_KEY],
                ),
                score=Score(value=score),
            )
            for document, score in hits
        ]

    @staticmethod
    def _category_filter(criteria: SearchCriteria) -> models.Filter | None:
        if criteria.category is None:
            return None
        return models.Filter(
            must=[
                models.FieldCondition(
                    key=CATEGORY_PAYLOAD_KEY,
                    match=models.MatchValue(value=criteria.category.value),
                ),
            ],
        )
