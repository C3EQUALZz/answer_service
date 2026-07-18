from abc import abstractmethod
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from answer_service.domain.analytics.entities.query_log import QueryLog


class AnalyticsCommandGateway(Protocol):
    """Write-side persistence for recorded queries."""

    @abstractmethod
    async def add(self, query_log: QueryLog) -> None:
        raise NotImplementedError
