from abc import abstractmethod
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from answer_service.domain.indexing.entities.qa_pair import QAPair
    from answer_service.domain.indexing.value_objects.external_id import ExternalId


class QACatalogCommandGateway(Protocol):
    """Write-side persistence for the QA pair catalog (the sync source of truth)."""

    @abstractmethod
    async def add(self, pair: QAPair) -> None:
        raise NotImplementedError

    @abstractmethod
    async def read_by_id(self, external_id: ExternalId) -> QAPair | None:
        raise NotImplementedError

    @abstractmethod
    async def update(self, pair: QAPair) -> None:
        raise NotImplementedError

    @abstractmethod
    async def delete_by_id(self, external_id: ExternalId) -> None:
        raise NotImplementedError
