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
        if not 1 <= query.limit <= MAX_LIMIT:
            msg = f"limit must be between 1 and {MAX_LIMIT}, got {query.limit}."
            raise PaginationError(msg)

        queries = await self._analytics_query.read_unanswered_queries(
            query.period,
            query.limit,
        )
        return UnansweredQueriesResponse(period=query.period, queries=tuple(queries))
