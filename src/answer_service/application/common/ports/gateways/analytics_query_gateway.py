from abc import abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Sequence

    from answer_service.domain.analytics.value_objects.period import Period


@dataclass(frozen=True, slots=True)
class QueryStatistics:
    """Aggregated counters over the recorded queries in a period."""

    total: int
    unanswered: int
    average_latency_ms: float

    @property
    def answered(self) -> int:
        return self.total - self.unanswered

    @property
    def unanswered_rate(self) -> float:
        """Share of queries that found nothing, between 0 and 1."""
        if self.total == 0:
            return 0.0
        return self.unanswered / self.total


@dataclass(frozen=True, slots=True)
class QueryFrequency:
    """How often one distinct query text was asked."""

    text: str
    occurrences: int


class AnalyticsQueryGateway(Protocol):
    """Read-side projections over the recorded queries.

    Returns aggregated numbers rather than entities: a statistics page over
    millions of log rows must be answered by the database, not by loading them.
    """

    @abstractmethod
    async def read_statistics(self, period: Period) -> QueryStatistics:
        raise NotImplementedError

    @abstractmethod
    async def read_unanswered_queries(
        self,
        period: Period,
        limit: int,
    ) -> Sequence[QueryFrequency]:
        """Most frequent queries that returned nothing, most frequent first."""
        raise NotImplementedError

    @abstractmethod
    async def read_popular_queries(
        self,
        period: Period,
        limit: int,
    ) -> Sequence[QueryFrequency]:
        """Most frequent queries overall, most frequent first."""
        raise NotImplementedError
