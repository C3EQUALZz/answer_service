from abc import abstractmethod
from typing import Protocol

from answer_service.application.common.ports.search import IndexDocument
from answer_service.domain.indexing.entities.qa_pair import QAPair


class QAPairDocumentMapper(Protocol):
    """Flattens a catalog pair into the document the search stores accept.

    Only text crosses: the aggregate's identity and events stay behind, and the
    embedding is computed by the writer that owns the model.
    """

    @abstractmethod
    def to_document(self, pair: QAPair) -> IndexDocument:
        raise NotImplementedError
