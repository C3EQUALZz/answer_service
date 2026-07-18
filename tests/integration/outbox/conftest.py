from collections.abc import Awaitable, Callable

import pytest

from answer_service.application.common.ports.outbox import (
    OutboxCommandGateway,
    OutboxMessage,
)
from answer_service.application.common.ports.transaction_manager import (
    TransactionManager,
)
from tests.unit.factories.outbox_factories import make_outbox_message

type OutboxSeeder = Callable[[int], Awaitable[list[OutboxMessage]]]


@pytest.fixture()
def store_outbox_messages(
    arrange_outbox: OutboxCommandGateway,
    arrange_transaction: TransactionManager,
) -> OutboxSeeder:
    """Commits pending messages before the test reads them.

    Written against the ports, not the container: what a test arranges is
    "messages exist", and how they get there is the container's business.
    """

    async def store(count: int) -> list[OutboxMessage]:
        messages = [make_outbox_message() for _ in range(count)]
        for message in messages:
            await arrange_outbox.add(message)
        await arrange_transaction.commit()
        return messages

    return store
