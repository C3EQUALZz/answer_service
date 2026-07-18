from datetime import datetime
from typing import Self

from pydantic import BaseModel

from answer_service.application.queries.analytics.list_unanswered_queries.query import (
    UnansweredQueriesResponse,
)
from answer_service.presentation.http.v1.routes.statistics.get_statistics.schemas import (
    QueryFrequencySchema,
)


class UnansweredQueriesSchemaResponse(BaseModel):
    """Questions users asked that the catalog could not answer."""

    period_start: datetime
    period_end: datetime
    total_occurrences: int
    queries: list[QueryFrequencySchema]

    @classmethod
    def of(cls, response: UnansweredQueriesResponse) -> Self:
        return cls(
            period_start=response.period.start,
            period_end=response.period.end,
            total_occurrences=response.total_occurrences,
            queries=[QueryFrequencySchema.of(query) for query in response.queries],
        )
