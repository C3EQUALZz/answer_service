from typing import Any, final, override

from sqlalchemy import Row

from answer_service.application.common.ports.gateways import IndexingTaskView
from answer_service.infrastructure.mappers.indexing_task_view_mapper import (
    IndexingTaskViewMapper,
)


@final
class SqlAlchemyIndexingTaskViewMapper(IndexingTaskViewMapper):
    """Flattens a task row into the view the status endpoint serves.

    Written by hand rather than with adaptix: a ``Row`` carries no field types
    for a converter to introspect, and the mapping is not field-to-field
    anyway — ``stats`` and ``failure`` are nested objects whose members become
    flat columns, with ``failure`` absent on every task that has not failed.
    """

    @override
    def to_view(self, row: Row[Any]) -> IndexingTaskView:
        stats = row.stats
        failure = row.failure
        return IndexingTaskView(
            task_id=row.id,
            status=row.status,
            source=str(row.source),
            created_at=row.created_at,
            started_at=row.started_at,
            finished_at=row.finished_at,
            created=stats.created,
            updated=stats.updated,
            deleted=stats.deleted,
            skipped=stats.skipped,
            failure_code=failure.code if failure is not None else None,
            failure_message=failure.message if failure is not None else None,
        )
