from typing import Final, final, override

from answer_service.application.common.ports.outbox import (
    OutboxMessage,
    OutboxPublisher,
)
from answer_service.application.common.ports.task_manager import ProjectEventPayload
from answer_service.application.common.ports.task_manager.task_keys import (
    OUTBOX_TASK_KEY,
)
from answer_service.application.common.ports.task_manager.task_manager import (
    TaskScheduler,
)


@final
class TaskSchedulerOutboxPublisher(OutboxPublisher):
    """Delivers outbox messages as background tasks instead of broker messages.

    The only consumer of our domain events is our own projector (Qdrant + FTS),
    so the task queue *is* the transport — no separate broker is involved.

    The background task id is derived from ``OutboxMessage.id``, which is stable
    across relay retries. A redelivered message therefore lands on the same task
    id, which is what an inbox check keys off to drop the duplicate.
    """

    def __init__(self, task_scheduler: TaskScheduler) -> None:
        self._task_scheduler: Final[TaskScheduler] = task_scheduler

    @override
    async def publish(self, message: OutboxMessage) -> None:
        task_id = self._task_scheduler.make_task_id(OUTBOX_TASK_KEY, message.id)
        await self._task_scheduler.schedule(
            task_id,
            ProjectEventPayload(
                message_id=message.id,
                event_type=message.event_type,
                payload=message.payload,
            ),
        )
