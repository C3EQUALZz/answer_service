from datetime import datetime
from typing import Self

from pydantic import BaseModel

from answer_service.application.common.ports.gateways import QueryFrequency
from answer_service.application.queries.analytics.get_statistics.query import (
    StatisticsResponse,
)


class QueryFrequencySchema(BaseModel):
    """How often one distinct query was asked."""

    text: str
    occurrences: int

    @classmethod
    def of(cls, frequency: QueryFrequency) -> Self:
        return cls(text=frequency.text, occurrences=frequency.occurrences)


class CatalogStatisticsSchema(BaseModel):
    """How much content the catalog holds right now."""

    total_pairs: int
    category_count: int
    pairs_per_category: dict[str, int]


class QueryStatisticsSchema(BaseModel):
    """How the service was used over the period."""

    total: int
    answered: int
    unanswered: int
    unanswered_rate: float
    average_latency_ms: float


class StatisticsSchemaResponse(BaseModel):
    """The service's report: what it holds and how it is used."""

    period_start: datetime
    period_end: datetime
    catalog: CatalogStatisticsSchema
    queries: QueryStatisticsSchema
    popular_queries: list[QueryFrequencySchema]

    @classmethod
    def of(cls, response: StatisticsResponse) -> Self:
        return cls(
            period_start=response.period.start,
            period_end=response.period.end,
            catalog=CatalogStatisticsSchema(
                total_pairs=response.catalog.total_pairs,
                category_count=response.catalog.category_count,
                pairs_per_category=dict(response.catalog.pairs_per_category),
            ),
            queries=QueryStatisticsSchema(
                total=response.queries.total,
                answered=response.queries.answered,
                unanswered=response.queries.unanswered,
                unanswered_rate=response.queries.unanswered_rate,
                average_latency_ms=response.queries.average_latency_ms,
            ),
            popular_queries=[
                QueryFrequencySchema.of(query) for query in response.popular_queries
            ],
        )
