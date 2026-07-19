from typing import Final, final, override

from answer_service.application.common.ports.outbox import (
    OutboxMessage,
    OutboxPublisher,
)
from answer_service.application.common.ports.task_manager.task_manager import (
    TaskScheduler,
)
from answer_service.infrastructure.adapters.messaging.outbox_routes import route_for


@final
class TaskSchedulerOutboxPublisher(OutboxPublisher):
    """Delivers outbox messages as background tasks instead of broker messages.

    The consumers of our domain events are our own background tasks, so the task
    queue *is* the transport — no separate broker is involved. Which task a given
    event becomes is declared in ``outbox_routes``; this class only carries it
    out.

    Routing here rather than at the point the event is raised is what keeps the
    publish after the commit. ``EnqueueIndexingHandler`` runs inside the
    transaction, so scheduling the run from there raced the commit and the
    worker could look up a task row that was not visible yet.

    The background task id is derived from the route's correlation field, which
    is stable across relay retries. A redelivered message therefore lands on the
    same task id, which is what an inbox check keys off to drop the duplicate.
    """

    def __init__(self, task_scheduler: TaskScheduler) -> None:
        self._task_scheduler: Final[TaskScheduler] = task_scheduler

    @override
    async def publish(self, message: OutboxMessage) -> None:
        route = route_for(message.event_type)
        task_id = self._task_scheduler.make_task_id(
            route.task_key,
            route.subject_of(message),
        )
        await self._task_scheduler.schedule(task_id, route.build_payload(message))
