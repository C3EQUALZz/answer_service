from uuid import UUID

from answer_service.application.common.ports.task_manager.payloads.base import (
    TaskPayload,
)


class ProjectEventPayload(TaskPayload):
    """Payload handed to the worker that projects a domain event downstream.

    ``message_id`` is the outbox row id, which never changes across relay
    retries — consumers use it as the idempotency key. ``payload`` is the
    serialized event body as stored in the outbox.
    """

    message_id: UUID
    event_type: str
    payload: str
