from abc import abstractmethod
from typing import Protocol

from .outbox_message import OutboxMessage


class OutboxCommandGateway(Protocol):
    @abstractmethod
    async def add(self, message: OutboxMessage) -> None: ...
