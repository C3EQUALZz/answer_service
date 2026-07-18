from dataclasses import dataclass
from uuid import UUID

from answer_service.application.common.mediator.markers import Command


@dataclass(frozen=True, slots=True)
class ProjectEventCommand(Command[None]):
    """Applies one relayed domain event to the search index.

    Dispatched by the worker for every message the outbox relay hands over.
    ``message_id`` is the outbox row id, stable across redeliveries, so it can
    serve as the idempotency key for an inbox check.
    """

    message_id: UUID
    event_type: str
    payload: str
