import logging
from typing import TYPE_CHECKING, Final, final, override
from uuid import NAMESPACE_URL, uuid5

from langchain_qdrant import QdrantVectorStore

from answer_service.application.common.ports.search import (
    IndexDocument,
    SearchIndexWriter,
)
from answer_service.infrastructure.errors import SearchIndexError
from answer_service.infrastructure.mappers.index_metadata_mapper import (
    IndexMetadataMapper,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from answer_service.domain.indexing.value_objects.external_id import ExternalId

logger: Final[logging.Logger] = logging.getLogger(__name__)


def point_id_of(external_id: ExternalId) -> str:
    """Derives the Qdrant point id from a source-provided external id.

    Qdrant accepts only UUIDs or integers as point ids, while an external id is
    an arbitrary string from the customer's file. Hashing it into a UUIDv5 keeps
    the mapping deterministic, which is what makes ``upsert`` idempotent: the
    same pair always lands on the same point and overwrites itself instead of
    accumulating duplicates on every re-index.
    """
    return str(uuid5(NAMESPACE_URL, external_id.value))


@final
class QdrantSearchIndexWriter(SearchIndexWriter):
    """Keeps the dense half of the search index in step with the catalog.

    Embedding happens inside the vector store, which owns the model — the
    application hands over text and never sees a vector.
    """

    def __init__(
        self,
        vector_store: QdrantVectorStore,
        metadata_mapper: IndexMetadataMapper,
    ) -> None:
        self._vector_store: Final[QdrantVectorStore] = vector_store
        self._metadata_mapper: Final[IndexMetadataMapper] = metadata_mapper

    @override
    async def upsert(self, documents: Sequence[IndexDocument]) -> None:
        if not documents:
            return

        try:
            await self._vector_store.aadd_texts(
                texts=[self._embeddable_text(document) for document in documents],
                metadatas=[
                    self._metadata_mapper.to_metadata(document) for document in documents
                ],
                ids=[point_id_of(document.external_id) for document in documents],
            )
        except Exception as e:
            msg = f"Failed to upsert {len(documents)} document(s) into Qdrant."
            raise SearchIndexError(msg) from e

        logger.debug("Upserted %d document(s) into Qdrant", len(documents))

    @override
    async def delete(self, external_ids: Sequence[ExternalId]) -> None:
        if not external_ids:
            return

        try:
            await self._vector_store.adelete(
                ids=[point_id_of(external_id) for external_id in external_ids],
            )
        except Exception as e:
            msg = f"Failed to delete {len(external_ids)} document(s) from Qdrant."
            raise SearchIndexError(msg) from e

        logger.debug("Deleted %d document(s) from Qdrant", len(external_ids))

    @staticmethod
    def _embeddable_text(document: IndexDocument) -> str:
        """Embeds question and answer together.

        A user's phrasing may match either side — the wording of the question or
        a term that only appears in the answer — so indexing them as one passage
        catches both instead of forcing a choice.
        """
        return f"{document.question}\n\n{document.answer}"
