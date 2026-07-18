from dataclasses import dataclass, field
from typing import Final

from answer_service.application.common.mediator.markers import Query
from answer_service.application.common.ports.gateways import (
    CatalogStatistics,
    QueryFrequency,
    QueryStatistics,
)
from answer_service.application.common.query_params.pagination import Pagination
from answer_service.application.common.query_params.sorting import SortingOrder
from answer_service.domain.analytics.value_objects.period import Period

DEFAULT_PERIOD_DAYS: Final[int] = 30
DEFAULT_POPULAR_LIMIT: Final[int] = 10


@dataclass(frozen=True, slots=True)
class StatisticsResponse:
    """The service's overall report: what it holds, and how it is being used."""

    period: Period
    catalog: CatalogStatistics
    queries: QueryStatistics
    popular_queries: tuple[QueryFrequency, ...]


@dataclass(frozen=True, slots=True)
class GetStatisticsQuery(Query[StatisticsResponse]):
    """Builds the statistics report for a period.

    The catalog half is a snapshot of *now* and ignores the period: a QA pair
    has no history in this model, so counting it as of a past date would be a
    number the data cannot support.
    """

    period: Period = field(default_factory=lambda: Period.last_days(DEFAULT_PERIOD_DAYS))
    popular_pagination: Pagination = field(
        default_factory=lambda: Pagination(limit=DEFAULT_POPULAR_LIMIT),
    )
    sorting_order: SortingOrder = SortingOrder.DESC
