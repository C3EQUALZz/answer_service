from dataclasses import dataclass
from enum import StrEnum
from typing import NewType

TaskKey = NewType("TaskKey", str)
TaskID = NewType("TaskID", str)


class TaskInfoStatus(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"
    STARTED = "started"
    RETRYING = "retrying"
    PROCESSING = "processing"


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskInfo:
    task_id: TaskID
    status: TaskInfoStatus
    description: str
