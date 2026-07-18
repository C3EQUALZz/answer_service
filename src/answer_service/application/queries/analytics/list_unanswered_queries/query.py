from dataclasses import dataclass, field
from typing import Final

from answer_service.application.common.mediator.markers import Query
from answer_service.application.common.ports.gateways import QueryFrequency
from answer_service.domain.analytics.value_objects.period import Period

DEFAULT_PERIOD_DAYS: Final[int] = 30
DEFAULT_LIMIT: Final[int] = 20


@dataclass(frozen=True, slots=True)
class UnansweredQueriesResponse:
    """Queries users asked that the catalog could not answer."""

    period: Period
    queries: tuple[QueryFrequency, ...]

    @property
    def total_occurrences(self) -> int:
        return sum(query.occurrences for query in self.queries)


@dataclass(frozen=True, slots=True)
class ListUnansweredQueriesQuery(Query[UnansweredQueriesResponse]):
    """Lists the most frequent queries that returned nothing.

    The actionable half of the statistics: each entry is a question users keep
    asking that the FAQ does not cover yet.
    """

    period: Period = field(default_factory=lambda: Period.last_days(DEFAULT_PERIOD_DAYS))
    limit: int = DEFAULT_LIMIT
