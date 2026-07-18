import logging
from typing import TYPE_CHECKING, Any, Final, override

from taskiq import AsyncBroker, ScheduleSource
from taskiq.depends.progress_tracker import TaskState

from answer_service.application.common.ports.task_manager.payloads.base import (
    TaskPayload,
)
from answer_service.application.common.ports.task_manager.task_id import (
    TaskID,
    TaskInfo,
    TaskInfoStatus,
    TaskKey,
)
from answer_service.application.common.ports.task_manager.task_manager import (
    TaskScheduler,
)
from answer_service.infrastructure.errors import UnregisteredTaskError

if TYPE_CHECKING:
    from collections.abc import Mapping

    from taskiq.depends.progress_tracker import TaskProgress

logger: Final[logging.Logger] = logging.getLogger(__name__)

TASK_STATUSES: Final[Mapping[str, TaskInfoStatus]] = {
    TaskState.STARTED: TaskInfoStatus.STARTED,
    TaskState.FAILURE: TaskInfoStatus.FAILURE,
    TaskState.SUCCESS: TaskInfoStatus.SUCCESS,
    TaskState.RETRY: TaskInfoStatus.RETRYING,
}


class TaskIQTaskScheduler(TaskScheduler):
    """TaskScheduler backed by a taskiq broker.

    Task ids are ``"<key>:<value>"``: the key names the registered task, the
    value makes the id unique and stable for that piece of work. Passing it to
    taskiq as the message id is what makes a redelivered schedule land on the
    same id, which the inbox check keys off.
    """

    def __init__(self, broker: AsyncBroker, schedule_source: ScheduleSource) -> None:
        self._broker: Final[AsyncBroker] = broker
        self._schedule_source: Final[ScheduleSource] = schedule_source

    @override
    async def schedule(self, task_id: TaskID, payload: TaskPayload) -> None:
        task_name = task_id.split(":")[0]

        task = self._broker.get_all_tasks().get(task_name)
        if task is None:
            msg = f"No task registered for '{task_name}'."
            raise UnregisteredTaskError(msg)

        await task.kicker().with_task_id(task_id).kiq(payload)
        logger.info("Scheduled task %s", task_id)

    @override
    async def read_task_info(self, task_id: TaskID) -> TaskInfo | None:
        progress: (
            TaskProgress[str] | None
        ) = await self._broker.result_backend.get_progress(task_id)
        if progress is None:
            return None

        return TaskInfo(
            task_id=task_id,
            status=TASK_STATUSES.get(progress.state, TaskInfoStatus.STARTED),
            description=progress.meta if progress.meta is not None else "",
        )

    @override
    def make_task_id(self, key: TaskKey, value: Any) -> TaskID:
        return TaskID(f"{key}:{value}")
