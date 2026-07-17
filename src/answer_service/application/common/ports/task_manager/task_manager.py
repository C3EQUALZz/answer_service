from abc import abstractmethod
from typing import Any, Protocol

from .payloads.base import TaskPayload
from .task_id import (
    TaskID,
    TaskInfo,
    TaskKey,
)


class TaskScheduler(Protocol):
    @abstractmethod
    async def schedule(
        self,
        task_id: TaskID,
        payload: TaskPayload,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def read_task_info(self, task_id: TaskID) -> TaskInfo | None:
        raise NotImplementedError

    @abstractmethod
    def make_task_id(self, key: TaskKey, value: Any) -> TaskID:
        raise NotImplementedError
