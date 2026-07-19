import logging
from typing import Final, override

from answer_service.application.common.mediator.handlers import QueryHandler
from answer_service.application.common.ports.gateways import (
    AnalyticsQueryGateway,
    QueryLogFilters,
)
from answer_service.application.error import PaginationError
from answer_service.application.queries.analytics.list_query_logs.query import (
    ListQueryLogsQuery,
    ListQueryLogsResponse,
)

MAX_LIMIT: Final[int] = 200


logger: Final[logging.Logger] = logging.getLogger(__name__)


class ListQueryLogsHandler(QueryHandler[ListQueryLogsQuery, ListQueryLogsResponse]):
    """Serves one page of the request journal, with its total.

    The ceiling on ``limit`` is enforced here rather than left to the gateway:
    the journal is the highest-volume table in the service, and an unbounded
    page would let one request pull the whole of it into memory.
    """

    def __init__(self, analytics_query: AnalyticsQueryGateway) -> None:
        self._analytics_query: Final[AnalyticsQueryGateway] = analytics_query

    @override
    async def handle(self, query: ListQueryLogsQuery) -> ListQueryLogsResponse:
        limit = query.pagination.limit
        logger.info(
            "list_query_logs: period %s .. %s, kind=%s, status=%s, limit=%s",
            query.period.start,
            query.period.end,
            query.kind,
            query.status,
            limit,
        )

        if limit is not None and limit > MAX_LIMIT:
            logger.warning(
                "list_query_logs: rejected limit %d, ceiling is %d",
                limit,
                MAX_LIMIT,
            )
            msg = f"limit must not exceed {MAX_LIMIT}, got {limit}."
            raise PaginationError(msg)

        filters = QueryLogFilters(
            period=query.period,
            kind=query.kind,
            status=query.status,
        )
        entries = await self._analytics_query.read_query_logs(
            filters,
            query.pagination,
            query.sorting_order,
        )
        total = await self._analytics_query.count_query_logs(filters)
        logger.info("list_query_logs: %d of %d entries returned", len(entries), total)

        return ListQueryLogsResponse(
            period=query.period,
            entries=tuple(entries),
            total=total,
        )
