from typing import Any, final, override

from sqlalchemy import Row

from answer_service.application.common.ports.gateways import QueryLogEntry
from answer_service.infrastructure.mappers.query_log_entry_mapper import (
    QueryLogEntryMapper,
)


@final
class SqlAlchemyQueryLogEntryMapper(QueryLogEntryMapper):
    """Unwraps a query-log row into the entry the listing serves.

    By hand rather than with adaptix: a ``Row`` carries no field types for a
    converter to introspect, and the mapping unwraps value objects
    (``text.content``, ``latency_ms.milliseconds``) and flattens the two nullable
    ones (``error_code``, ``category``) that are absent on an ordinary success.
    """

    @override
    def to_entry(self, row: Row[Any]) -> QueryLogEntry:
        return QueryLogEntry(
            request_id=row.id,
            kind=row.kind,
            text=row.text.content,
            occurred_at=row.occurred_at,
            latency_ms=row.latency_ms.milliseconds,
            results_count=row.results_count,
            top_score=row.top_score,
            status=row.status,
            error_code=row.error_code.value if row.error_code is not None else None,
            category=row.category.value if row.category is not None else None,
        )
