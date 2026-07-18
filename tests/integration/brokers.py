"""A broker that records what was scheduled instead of running it."""

from typing import Final, override

from taskiq import AsyncBroker, BrokerMessage, InMemoryBroker
from taskiq.exceptions import UnknownTaskError


class RecordingBroker(InMemoryBroker):
    """Accepts kicks, resolves the task, and stops there.

    The production tasks are registered on it normally, so the name resolution
    the scheduler depends on is the real one — that is the failure these tests
    exist to catch.

    Execution is where it diverges. ``InMemoryBroker`` runs a kicked task in a
    background coroutine, which would put the whole sync in flight *while the
    assertions run*: a test checking that a task is ``QUEUED`` would race the
    worker completing it. Recording instead keeps the scheduling observable and
    the timing deterministic.
    """

    def __init__(self) -> None:
        super().__init__()
        self.kicked: Final[list[BrokerMessage]] = []

    @override
    async def kick(self, message: BrokerMessage) -> None:
        if self.find_task(message.task_name) is None:
            raise UnknownTaskError(task_name=message.task_name)
        self.kicked.append(message)

    @property
    def kicked_task_names(self) -> list[str]:
        return [message.task_name for message in self.kicked]

    def forget_kicked(self) -> None:
        self.kicked.clear()


def is_recording(broker: AsyncBroker) -> bool:
    return isinstance(broker, RecordingBroker)
