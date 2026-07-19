import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Final
from uuid import UUID

from answer_service.application.common.ports.outbox import OutboxMessage
from answer_service.application.common.ports.task_manager import (
    ProjectEventPayload,
    RunIndexingPayload,
)
from answer_service.application.common.ports.task_manager.payloads.base import (
    TaskPayload,
)
from answer_service.application.common.ports.task_manager.task_id import TaskKey
from answer_service.application.common.ports.task_manager.task_keys import (
    INDEXING_TASK_KEY,
    OUTBOX_TASK_KEY,
)
from answer_service.application.error import MalformedEventPayloadError
from answer_service.domain.indexing.events import IndexingTaskQueued

VALUE_KEY: Final[str] = "value"
TASK_ID_FIELD: Final[str] = "task_id"


@dataclass(frozen=True, slots=True)
class OutboxRoute:
    """Which background task an outbox message becomes, and what it carries.

    ``correlates_on`` names the payload field identifying the work. The task id
    is derived from it so a redelivered message lands on the id an inbox check
    already knows; left unset, the message id plays that role.
    """

    task_key: TaskKey
    build_payload: Callable[[OutboxMessage], TaskPayload]
    correlates_on: str | None = None

    def subject_of(self, message: OutboxMessage) -> UUID:
        if self.correlates_on is None:
            return message.id
        return uuid_field(message, self.correlates_on)


def uuid_field(message: OutboxMessage, field: str) -> UUID:
    """Reads a UUID-valued field, stored bare or wrapped in a value object."""
    try:
        payload: dict[str, Any] = json.loads(message.payload)
        raw = payload[field]
        return UUID(raw[VALUE_KEY] if isinstance(raw, dict) else raw)
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
        msg = (
            f"Event '{message.event_type}' (message '{message.id}') "
            f"carries no readable {field}."
        )
        raise MalformedEventPayloadError(msg) from e


def _project_event(message: OutboxMessage) -> TaskPayload:
    return ProjectEventPayload(
        message_id=message.id,
        event_type=message.event_type,
        payload=message.payload,
    )


def _run_indexing(message: OutboxMessage) -> TaskPayload:
    return RunIndexingPayload(task_id=uuid_field(message, TASK_ID_FIELD))


PROJECTION_ROUTE: Final[OutboxRoute] = OutboxRoute(
    task_key=OUTBOX_TASK_KEY,
    build_payload=_project_event,
)

# Keyed by event type name, the way ExceptionHandler._ERROR_MAPPING is keyed by
# error type. Anything absent goes to the projector, which ignores what it does
# not recognise — so adding a domain event stays a no-op here until that event
# needs somewhere else to go.
EVENT_ROUTES: Final[Mapping[str, OutboxRoute]] = MappingProxyType(
    {
        IndexingTaskQueued.__name__: OutboxRoute(
            task_key=INDEXING_TASK_KEY,
            build_payload=_run_indexing,
            correlates_on=TASK_ID_FIELD,
        ),
    },
)


def route_for(event_type: str) -> OutboxRoute:
    return EVENT_ROUTES.get(event_type, PROJECTION_ROUTE)
