from typing import Final

from .task_id import TaskKey

INDEXING_TASK_KEY: Final[TaskKey] = TaskKey("indexing")
OUTBOX_TASK_KEY: Final[TaskKey] = TaskKey("outbox")

RELAY_OUTBOX_TASK_NAME: Final[str] = "relay_outbox"
