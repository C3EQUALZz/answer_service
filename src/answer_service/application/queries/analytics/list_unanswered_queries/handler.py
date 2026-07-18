from typing import Final, override

from answer_service.application.common.mediator.handlers import QueryHandler
from answer_service.application.common.ports.gateways import AnalyticsQueryGateway
from answer_service.application.error import PaginationError
from answer_service.application.queries.analytics.list_unanswered_queries.query import (
    ListUnansweredQueriesQuery,
    UnansweredQueriesResponse,
)

MAX_LIMIT: Final[int] = 200


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
        # ``Pagination`` already rejects a non-positive limit; the ceiling is
        # this endpoint's own, so one caller cannot ask for the whole log.
        limit = query.pagination.limit
        if limit is not None and limit > MAX_LIMIT:
            msg = f"limit must not exceed {MAX_LIMIT}, got {limit}."
            raise PaginationError(msg)

        queries = await self._analytics_query.read_unanswered_queries(
            query.period,
            query.pagination,
            query.sorting_order,
        )
        return UnansweredQueriesResponse(period=query.period, queries=tuple(queries))
