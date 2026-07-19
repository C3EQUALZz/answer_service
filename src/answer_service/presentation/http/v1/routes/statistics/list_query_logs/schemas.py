from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel

from answer_service.application.common.ports.gateways import QueryLogEntry
from answer_service.application.queries.analytics.list_query_logs.query import (
    ListQueryLogsResponse,
)


class QueryLogEntrySchema(BaseModel):
    """One recorded request, exactly as §9 of the brief enumerates it.

    ``request_id`` is the identifier the search and ask endpoints returned, so a
    caller can find their own request here and read how it went.
    """

    request_id: UUID
    kind: str
    query: str
    occurred_at: datetime
    duration_ms: int
    results_count: int
    top_score: float | None
    status: str
    error_code: str | None
    category: str | None

    @classmethod
    def of(cls, entry: QueryLogEntry) -> Self:
        return cls(
            request_id=entry.request_id,
            kind=entry.kind.value,
            query=entry.text,
            occurred_at=entry.occurred_at,
            duration_ms=entry.latency_ms,
            results_count=entry.results_count,
            top_score=entry.top_score,
            status=entry.status.value,
            error_code=entry.error_code,
            category=entry.category,
        )


class QueryLogsSchemaResponse(BaseModel):
    """One page of the request journal.

    ``total`` counts every entry matching the filters, not just this page: it is
    what tells a caller paging through whether another page is waiting.
    """

    period_start: datetime
    period_end: datetime
    total: int
    entries: list[QueryLogEntrySchema]

    @classmethod
    def of(cls, response: ListQueryLogsResponse) -> Self:
        return cls(
            period_start=response.period.start,
            period_end=response.period.end,
            total=response.total,
            entries=[QueryLogEntrySchema.of(entry) for entry in response.entries],
        )
