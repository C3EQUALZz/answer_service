from typing import Final

from sqlalchemy import (
    UUID as SA_UUID,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    Table,
    text,
)
from sqlalchemy.orm import composite

from answer_service.domain.analytics.entities.query_log import QueryLog
from answer_service.domain.analytics.value_objects.query_outcome import QueryOutcome
from answer_service.infrastructure.persistence.models.base import mapper_registry
from answer_service.infrastructure.persistence.models.types import (
    CategoryLabelType,
    LatencyType,
    QueryKindType,
    QueryTextType,
)

query_logs_table: Final[Table] = Table(
    "query_logs",
    mapper_registry.metadata,
    Column("id", SA_UUID(as_uuid=True), primary_key=True),
    Column("text", QueryTextType, nullable=False),
    Column("kind", QueryKindType, nullable=False, index=True),
    Column("results_count", Integer, nullable=False),
    Column("top_score", Float, nullable=True),
    Column("latency_ms", LatencyType, nullable=False),
    Column("category", CategoryLabelType, nullable=True, index=True),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    # Every report filters by period first, then groups by text. A composite
    # index in that order serves both steps, and also covers the period-only
    # lookups — a separate index on occurred_at would be dead weight on write.
    Index("ix_query_logs_occurred_at_text", "occurred_at", "text"),
    # The gap report only ever looks at queries that found nothing, which is the
    # small minority of rows. A partial index keeps it proportional to those.
    Index(
        "ix_query_logs_unanswered",
        "occurred_at",
        postgresql_where=text("results_count = 0"),
    ),
)


def map_query_logs_table() -> None:
    """Maps the QueryLog entity.

    ``outcome`` is a composite over two real columns rather than a JSONB blob:
    ``results_count`` is filtered on by every statistics query, and a value
    buried in JSON could not be indexed for it.
    """
    mapper_registry.map_imperatively(
        QueryLog,
        query_logs_table,
        properties={
            "id": query_logs_table.c.id,
            "text": query_logs_table.c.text,
            "kind": query_logs_table.c.kind,
            "outcome": composite(
                QueryOutcome,
                query_logs_table.c.results_count,
                query_logs_table.c.top_score,
            ),
            "latency": query_logs_table.c.latency_ms,
            "category": query_logs_table.c.category,
            "occurred_at": query_logs_table.c.occurred_at,
            "created_at": query_logs_table.c.created_at,
            "updated_at": query_logs_table.c.updated_at,
        },
    )
