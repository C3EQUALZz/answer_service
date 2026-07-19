from abc import abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Protocol
from uuid import UUID

from answer_service.domain.analytics.value_objects.period import Period
from answer_service.domain.analytics.value_objects.query_kind import QueryKind
from answer_service.domain.analytics.value_objects.query_status import QueryStatus

if TYPE_CHECKING:
    from collections.abc import Sequence

    from answer_service.application.common.query_params.pagination import Pagination
    from answer_service.application.common.query_params.sorting import SortingOrder


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


@dataclass(frozen=True, slots=True)
class QueryLogEntry:
    """One journalled request, as the statistics listing renders it.

    A row, not an aggregate: this is the audit trail a caller pages through to
    find their own request by id, which is why it carries the identifier the
    search and ask endpoints hand back rather than a count.
    """

    request_id: UUID
    kind: QueryKind
    text: str
    occurred_at: datetime
    latency_ms: int
    results_count: int
    top_score: float | None
    status: QueryStatus
    error_code: str | None
    category: str | None


@dataclass(frozen=True, slots=True)
class QueryLogFilters:
    """What narrows the statistics listing.

    One object rather than four parameters because every caller passes the
    whole set: the gateway needs the same predicate to page the rows and to
    count them, and two argument lists that must stay identical are two that
    eventually will not.
    """

    period: Period
    kind: QueryKind | None = None
    status: QueryStatus | None = None


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
        pagination: Pagination,
        sorting_order: SortingOrder,
    ) -> Sequence[QueryFrequency]:
        """Queries that returned nothing, ranked by how often they were asked.

        Paginated because the gap report is a backlog someone works through:
        the second page is the next batch of FAQ entries to write, not a rerun
        of the first.
        """
        raise NotImplementedError

    @abstractmethod
    async def read_popular_queries(
        self,
        period: Period,
        pagination: Pagination,
        sorting_order: SortingOrder,
    ) -> Sequence[QueryFrequency]:
        """Queries overall, ranked by how often they were asked."""
        raise NotImplementedError

    @abstractmethod
    async def read_query_logs(
        self,
        filters: QueryLogFilters,
        pagination: Pagination,
        sorting_order: SortingOrder,
    ) -> Sequence[QueryLogEntry]:
        """One page of the journal, ordered by when each request arrived.

        Ordered by ``occurred_at`` with the identifier as a tie-break: requests
        served in the same millisecond would otherwise be free to swap places
        between pages, and a caller paging through would see one row twice and
        another never.
        """
        raise NotImplementedError

    @abstractmethod
    async def count_query_logs(self, filters: QueryLogFilters) -> int:
        """How many entries match, so a caller knows how far the pages go."""
        raise NotImplementedError
