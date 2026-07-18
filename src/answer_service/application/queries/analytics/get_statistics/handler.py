from typing import Final, override

from answer_service.application.common.mediator.handlers import QueryHandler
from answer_service.application.common.ports.gateways import (
    AnalyticsQueryGateway,
    QACatalogQueryGateway,
)
from answer_service.application.queries.analytics.get_statistics.query import (
    GetStatisticsQuery,
    StatisticsResponse,
)


class GetStatisticsHandler(QueryHandler[GetStatisticsQuery, StatisticsResponse]):
    """Assembles the report from the catalog and the query log.

    Both halves are aggregated by their gateway, so the handler composes three
    numbers rather than iterating rows — the report stays constant-cost as the
    log grows.
    """

    def __init__(
        self,
        catalog_query: QACatalogQueryGateway,
        analytics_query: AnalyticsQueryGateway,
    ) -> None:
        self._catalog_query: Final[QACatalogQueryGateway] = catalog_query
        self._analytics_query: Final[AnalyticsQueryGateway] = analytics_query

    @override
    async def handle(self, query: GetStatisticsQuery) -> StatisticsResponse:
        catalog = await self._catalog_query.read_statistics()
        queries = await self._analytics_query.read_statistics(query.period)
        popular = await self._analytics_query.read_popular_queries(
            query.period,
            query.popular_limit,
        )

        return StatisticsResponse(
            period=query.period,
            catalog=catalog,
            queries=queries,
            popular_queries=tuple(popular),
        )
