from uuid import UUID

from answer_service.application.common.ports.task_manager.payloads.base import (
    TaskPayload,
)
from answer_service.application.common.ports.task_manager.payloads.event_bodies import (
    EventBody,
)


class OutboxEventPayload[BodyT: EventBody](TaskPayload):
    """The single shape every relayed domain event takes on the task queue.

    One envelope for all tasks is what lets the publisher stay generic: it knows
    the outbox row, not the task, and the task name is the event name. Each task
    parametrizes ``BodyT`` with the model it expects, and taskiq validates the
    body into that type on the way in.

    ``message_id`` is the outbox row id, unchanged across relay redeliveries, so
    it identifies the delivery rather than the work.
    """

    message_id: UUID
    event_type: str
    body: BodyT
