import json
import logging
from typing import Final, final, override

from answer_service.application.common.ports.outbox import (
    OutboxMessage,
    OutboxPublisher,
)
from answer_service.application.common.ports.task_manager import (
    OutboxEventPayload,
    RawEventBody,
)
from answer_service.application.common.ports.task_manager.task_id import TaskKey
from answer_service.application.common.ports.task_manager.task_manager import (
    TaskScheduler,
)

logger: Final[logging.Logger] = logging.getLogger(__name__)


@final
class TaskSchedulerOutboxPublisher(OutboxPublisher):
    """Delivers outbox messages as background tasks instead of broker messages.

    The consumers of our domain events are our own background tasks, so the task
    queue *is* the transport — no separate broker is involved. Every task is
    registered under the name of the event it reacts to, which is what lets this
    stay generic: it forwards the row and never learns what happens to it.

    An event with no registered task raises rather than being dropped. Adding a
    domain event therefore means adding its task, and forgetting shows up as a
    failing relay instead of silence.

    Publishing here rather than where the event is raised is what keeps it after
    the commit. ``EnqueueIndexingHandler`` runs inside the transaction, so
    scheduling from there raced the commit and the worker could look up a task
    row that was not visible yet.
    """

    def __init__(self, task_scheduler: TaskScheduler) -> None:
        self._task_scheduler: Final[TaskScheduler] = task_scheduler

    @override
    async def publish(self, message: OutboxMessage) -> None:
        task_id = self._task_scheduler.make_task_id(
            TaskKey(message.event_type),
            message.id,
        )
        logger.info(
            "outbox_publisher: scheduling %s as task %s",
            message.event_type,
            task_id,
        )

        await self._task_scheduler.schedule(
            task_id,
            OutboxEventPayload[RawEventBody](
                message_id=message.id,
                event_type=message.event_type,
                body=RawEventBody.model_validate(json.loads(message.payload)),
            ),
        )
