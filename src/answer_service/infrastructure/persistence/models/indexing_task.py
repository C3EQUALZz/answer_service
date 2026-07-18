from typing import Final

from sqlalchemy import (
    UUID as SA_UUID,
    Column,
    DateTime,
    Table,
)

from answer_service.domain.indexing.entities.indexing_task import IndexingTask
from answer_service.infrastructure.persistence.models.base import mapper_registry
from answer_service.infrastructure.persistence.models.types import (
    FailureInfoType,
    IndexingTaskStatusType,
    SourceReferenceType,
    SyncStatsType,
)

indexing_tasks_table: Final[Table] = Table(
    "indexing_tasks",
    mapper_registry.metadata,
    Column("id", SA_UUID(as_uuid=True), primary_key=True),
    Column("source", SourceReferenceType, nullable=False),
    Column("status", IndexingTaskStatusType, nullable=False, index=True),
    Column("started_at", DateTime(timezone=True), nullable=True),
    Column("finished_at", DateTime(timezone=True), nullable=True),
    Column("stats", SyncStatsType, nullable=False),
    Column("failure", FailureInfoType, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)


def map_indexing_tasks_table() -> None:
    """Maps the IndexingTask aggregate."""
    mapper_registry.map_imperatively(
        IndexingTask,
        indexing_tasks_table,
        properties={
            "id": indexing_tasks_table.c.id,
            "source": indexing_tasks_table.c.source,
            "status": indexing_tasks_table.c.status,
            "started_at": indexing_tasks_table.c.started_at,
            "finished_at": indexing_tasks_table.c.finished_at,
            "stats": indexing_tasks_table.c.stats,
            "failure": indexing_tasks_table.c.failure,
            "created_at": indexing_tasks_table.c.created_at,
            "updated_at": indexing_tasks_table.c.updated_at,
        },
    )
