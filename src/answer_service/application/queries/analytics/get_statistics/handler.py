import logging
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

logger: Final[logging.Logger] = logging.getLogger(__name__)


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
        logger.info(
            "get_statistics: period %s .. %s",
            query.period.start,
            query.period.end,
        )

        catalog = await self._catalog_query.read_statistics()
        logger.info(
            "get_statistics: catalog holds %d pair(s) across %d category(ies)",
            catalog.total_pairs,
            catalog.category_count,
        )

        queries = await self._analytics_query.read_statistics(query.period)
        logger.info(
            "get_statistics: %d served, %d unanswered, average %.1f ms",
            queries.total,
            queries.unanswered,
            queries.average_latency_ms,
        )

        popular = await self._analytics_query.read_popular_queries(
            query.period,
            query.popular_pagination,
            query.sorting_order,
        )
        logger.info("get_statistics: %d popular query row(s)", len(popular))

        return StatisticsResponse(
            period=query.period,
            catalog=catalog,
            queries=queries,
            popular_queries=tuple(popular),
        )
