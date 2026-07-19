from dataclasses import dataclass, field
from typing import Final

from answer_service.application.common.mediator.markers import Query
from answer_service.application.common.ports.gateways import QueryLogEntry
from answer_service.application.common.query_params.pagination import Pagination
from answer_service.application.common.query_params.sorting import SortingOrder
from answer_service.domain.analytics.value_objects.period import Period
from answer_service.domain.analytics.value_objects.query_kind import QueryKind
from answer_service.domain.analytics.value_objects.query_status import QueryStatus

DEFAULT_PERIOD_DAYS: Final[int] = 30
DEFAULT_LIMIT: Final[int] = 20


@dataclass(frozen=True, slots=True)
class ListQueryLogsResponse:
    """One page of the request journal, and how large the whole journal is.

    ``total`` is the count *before* pagination, so a caller can tell whether
    another page exists without asking for it — the difference between "20
    results" and "20 of 4,000".
    """

    period: Period
    entries: tuple[QueryLogEntry, ...]
    total: int


@dataclass(frozen=True, slots=True)
class ListQueryLogsQuery(Query[ListQueryLogsResponse]):
    """Pages the recorded requests, newest first, narrowed by the given filters.

    The audit trail behind the aggregate report: where the statistics summary
    says *how many* failed, this says *which* — one row per request, with the
    identifier the search and ask endpoints handed the caller.

    A query rather than a command: it reads the journal and is itself not
    journalled, so it cannot recurse into the recording pipeline.
    """

    period: Period = field(default_factory=lambda: Period.last_days(DEFAULT_PERIOD_DAYS))
    kind: QueryKind | None = None
    status: QueryStatus | None = None
    pagination: Pagination = field(
        default_factory=lambda: Pagination(limit=DEFAULT_LIMIT),
    )
    sorting_order: SortingOrder = SortingOrder.DESC
