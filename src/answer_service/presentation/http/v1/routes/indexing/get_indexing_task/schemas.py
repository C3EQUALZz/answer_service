from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel

from answer_service.application.common.ports.gateways import IndexingTaskView


class SyncStatsSchema(BaseModel):
    """What the run changed in the catalog."""

    created: int
    updated: int
    deleted: int
    skipped: int


class IndexingTaskResponse(BaseModel):
    """Status of one synchronization run."""

    task_id: UUID
    status: str
    source: str
    is_finished: bool
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    stats: SyncStatsSchema
    failure_code: str | None
    failure_message: str | None

    @classmethod
    def of(cls, view: IndexingTaskView) -> Self:
        return cls(
            task_id=view.task_id,
            status=view.status.value,
            source=view.source,
            is_finished=view.is_finished,
            created_at=view.created_at,
            started_at=view.started_at,
            finished_at=view.finished_at,
            stats=SyncStatsSchema(
                created=view.created,
                updated=view.updated,
                deleted=view.deleted,
                skipped=view.skipped,
            ),
            failure_code=view.failure_code,
            failure_message=view.failure_message,
        )
