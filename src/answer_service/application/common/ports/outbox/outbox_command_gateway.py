from abc import abstractmethod
from typing import TYPE_CHECKING, Protocol

from .outbox_message import OutboxMessage

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID


class OutboxCommandGateway(Protocol):
    """Write-side access to the outbox.

    ``read_pending`` lives here rather than on a query gateway because it claims
    the rows it returns (``FOR UPDATE SKIP LOCKED``): it is a read taken with the
    intent to write, and it is only correct inside the relay's transaction.
    """

    @abstractmethod
    async def add(self, message: OutboxMessage) -> None: ...

    @abstractmethod
    async def read_pending(self, limit: int) -> Sequence[OutboxMessage]:
        raise NotImplementedError

    @abstractmethod
    async def mark_processed(self, message_id: UUID) -> None:
        raise NotImplementedError
