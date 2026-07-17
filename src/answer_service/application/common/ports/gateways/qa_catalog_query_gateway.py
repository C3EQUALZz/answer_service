from abc import abstractmethod
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Mapping

    from answer_service.domain.indexing.value_objects.content_hash import ContentHash
    from answer_service.domain.indexing.value_objects.external_id import ExternalId


class QACatalogQueryGateway(Protocol):
    """Read-side projections over the QA pair catalog."""

    @abstractmethod
    async def read_fingerprints(self) -> Mapping[ExternalId, ContentHash]:
        """Return the current ``external_id -> content_hash`` manifest for diffing."""
        raise NotImplementedError
