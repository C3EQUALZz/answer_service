from abc import abstractmethod
from typing import Protocol

from .outbox_message import OutboxMessage


class OutboxPublisher(Protocol):
    """Port for publishing a serialised outbox message to a message broker."""

    @abstractmethod
    async def publish(self, message: OutboxMessage) -> None:
        raise NotImplementedError
