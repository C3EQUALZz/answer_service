from abc import abstractmethod
from typing import Protocol

from answer_service.application.common.ports.search import IndexDocument


class IndexMetadataMapper(Protocol):
    """Renders a search document as the payload stored alongside its vector.

    Both this port and its implementation live in the infrastructure layer: a
    metadata dict is a vector-store concept, and the only caller is the writer
    that talks to Qdrant. Hoisting it into the application ports would put a
    storage detail in front of code that has no business knowing it.
    """

    @abstractmethod
    def to_metadata(self, document: IndexDocument) -> dict[str, str]:
        raise NotImplementedError
