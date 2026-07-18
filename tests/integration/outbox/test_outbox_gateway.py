"""The outbox against a real database, through its port.

``SELECT ... FOR UPDATE SKIP LOCKED`` is the whole reason the relay can run on
several replicas. It cannot be verified against a stub — the locking *is* the
behaviour — so these run on Postgres, while naming only the port, so the
persistence technology can change without touching them.
"""

from collections.abc import Sequence

import pytest
from dishka import AsyncContainer, FromDishka, Scope

from answer_service.application.common.ports.outbox import (
    OutboxCommandGateway,
    OutboxMessage,
)
from answer_service.application.common.ports.transaction_manager import (
    TransactionManager,
)
from tests.integration.inject import inject
from tests.integration.outbox.conftest import OutboxSeeder

pytestmark = [
    pytest.mark.asyncio(loop_scope="session"),
    pytest.mark.usefixtures("clean_tables"),
]


def ids(messages: Sequence[OutboxMessage]) -> set[str]:
    return {str(message.id) for message in messages}


@inject
async def test_a_stored_message_reads_back_unchanged(
    store_outbox_messages: OutboxSeeder,
    gateway: FromDishka[OutboxCommandGateway],
) -> None:
    [stored] = await store_outbox_messages(1)

    [loaded] = await gateway.read_pending(limit=10)

    assert loaded.id == stored.id
    assert loaded.event_type == stored.event_type
    assert loaded.payload == stored.payload
    assert loaded.processed_at is None


@inject
async def test_pending_messages_come_out_oldest_first(
    store_outbox_messages: OutboxSeeder,
    gateway: FromDishka[OutboxCommandGateway],
) -> None:
    """Events must reach the index in the order they happened."""
    stored = await store_outbox_messages(5)

    pending = await gateway.read_pending(limit=10)

    assert [message.id for message in pending] == [
        message.id for message in sorted(stored, key=lambda m: m.created_at)
    ]


@inject
async def test_the_limit_caps_the_batch(
    store_outbox_messages: OutboxSeeder,
    gateway: FromDishka[OutboxCommandGateway],
) -> None:
    await store_outbox_messages(5)

    pending = await gateway.read_pending(limit=2)

    assert len(pending) == 2


@inject
async def test_a_processed_message_stops_being_pending(
    store_outbox_messages: OutboxSeeder,
    gateway: FromDishka[OutboxCommandGateway],
    transaction: FromDishka[TransactionManager],
) -> None:
    [message] = await store_outbox_messages(1)

    await gateway.mark_processed(message.id)
    await transaction.commit()

    assert await gateway.read_pending(limit=10) == []


async def test_two_relays_never_claim_the_same_message(
    store_outbox_messages: OutboxSeeder,
    container: AsyncContainer,
) -> None:
    """The guarantee that lets the relay scale horizontally.

    Two request scopes stand in for two replicas: the first holds its rows until
    it commits, and the second must step over them rather than block or hand out
    the same work twice.
    """
    await store_outbox_messages(4)

    async with (
        container(scope=Scope.REQUEST) as first_replica,
        container(scope=Scope.REQUEST) as second_replica,
    ):
        first_batch = await (await first_replica.get(OutboxCommandGateway)).read_pending(
            limit=2,
        )
        second_batch = await (
            await second_replica.get(OutboxCommandGateway)
        ).read_pending(limit=2)

        assert len(first_batch) == 2
        assert len(second_batch) == 2
        assert ids(first_batch).isdisjoint(ids(second_batch))


async def test_a_second_relay_sees_nothing_when_all_rows_are_claimed(
    store_outbox_messages: OutboxSeeder,
    container: AsyncContainer,
) -> None:
    """Skipping locked rows means an empty batch, not a wait and not a duplicate."""
    await store_outbox_messages(2)

    async with (
        container(scope=Scope.REQUEST) as first_replica,
        container(scope=Scope.REQUEST) as second_replica,
    ):
        await (await first_replica.get(OutboxCommandGateway)).read_pending(limit=10)
        second_batch = await (
            await second_replica.get(OutboxCommandGateway)
        ).read_pending(limit=10)

        assert second_batch == []


async def test_rows_are_released_when_the_transaction_ends(
    store_outbox_messages: OutboxSeeder,
    container: AsyncContainer,
) -> None:
    """A relay that crashed must not strand its batch forever."""
    await store_outbox_messages(2)

    async with container(scope=Scope.REQUEST) as abandoned_replica:
        await (await abandoned_replica.get(OutboxCommandGateway)).read_pending(limit=10)
        await (await abandoned_replica.get(TransactionManager)).rollback()

    async with container(scope=Scope.REQUEST) as next_replica:
        recovered = await (await next_replica.get(OutboxCommandGateway)).read_pending(
            limit=10,
        )

    assert len(recovered) == 2
