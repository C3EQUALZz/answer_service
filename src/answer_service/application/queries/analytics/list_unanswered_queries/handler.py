import logging
from typing import Final, override

from answer_service.application.common.mediator.handlers import QueryHandler
from answer_service.application.common.ports.gateways import AnalyticsQueryGateway
from answer_service.application.error import PaginationError
from answer_service.application.queries.analytics.list_unanswered_queries.query import (
    ListUnansweredQueriesQuery,
    UnansweredQueriesResponse,
)

MAX_LIMIT: Final[int] = 200


logger: Final[logging.Logger] = logging.getLogger(__name__)


class ListUnansweredQueriesHandler(
    QueryHandler[ListUnansweredQueriesQuery, UnansweredQueriesResponse],
):
    """Reports the gaps in the catalog, most frequently hit first."""

    def __init__(self, analytics_query: AnalyticsQueryGateway) -> None:
        self._analytics_query: Final[AnalyticsQueryGateway] = analytics_query

    @override
    async def handle(
        self,
        query: ListUnansweredQueriesQuery,
    ) -> UnansweredQueriesResponse:
        limit = query.pagination.limit
        logger.info(
            "list_unanswered: period %s .. %s, limit %s",
            query.period.start,
            query.period.end,
            limit,
        )

        if limit is not None and limit > MAX_LIMIT:
            logger.warning(
                "list_unanswered: rejected limit %d, ceiling is %d",
                limit,
                MAX_LIMIT,
            )
            msg = f"limit must not exceed {MAX_LIMIT}, got {limit}."
            raise PaginationError(msg)

        queries = await self._analytics_query.read_unanswered_queries(
            query.period,
            query.pagination,
            query.sorting_order,
        )
        logger.info("list_unanswered: %d gap(s) reported", len(queries))
        return UnansweredQueriesResponse(period=query.period, queries=tuple(queries))
