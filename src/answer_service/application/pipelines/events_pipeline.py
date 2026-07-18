from typing import Any, Final, override

from answer_service.application.common.mediator.handlers import (
    HandleNext,
    PipelineHandler,
)
from answer_service.application.common.mediator.markers import Command
from answer_service.application.common.ports.outbox.event_bus import EventBus
from answer_service.domain.common.events_collection import EventsCollection


class EventsPipeline[TCommand: Command[Any], TResponse](
    PipelineHandler[TCommand, TResponse],
):
    """Drains and publishes the domain events collected during a command.

    ``EventsCollection`` is request-scoped and shared with the aggregates built
    inside the handler, so after the handler succeeds this pipeline pulls the
    events it recorded and hands them to the bus. It must run *inside* the
    transaction pipeline, so the events are persisted (to the outbox) atomically
    with the state change; on failure the handler raises, nothing is pulled, and
    the events are discarded with the rollback.
    """

    def __init__(
        self,
        events_collection: EventsCollection,
        event_bus: EventBus,
    ) -> None:
        self._events_collection: Final[EventsCollection] = events_collection
        self._event_bus: Final[EventBus] = event_bus

    @override
    async def handle(
        self,
        request: TCommand,
        handle_next: HandleNext[TCommand, TResponse],
    ) -> TResponse:
        response = await handle_next(request)
        events = self._events_collection.pull_events()
        await self._event_bus.publish(events)
        return response
