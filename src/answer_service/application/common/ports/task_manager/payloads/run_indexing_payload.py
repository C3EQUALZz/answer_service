from uuid import UUID

from answer_service.application.common.ports.task_manager.payloads.base import (
    TaskPayload,
)


class RunIndexingPayload(TaskPayload):
    """Payload handed to the background worker that runs a synchronization.

    Carries the identity of the already-persisted ``IndexingTask`` so the worker
    can pick it up, run the sync and record the outcome against it.
    """

    task_id: UUID
