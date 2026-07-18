from answer_service.application.commands.outbox.relay_outbox.command import (
    RelayOutboxCommand,
    RelayOutboxResponse,
)
from answer_service.application.commands.outbox.relay_outbox.handler import (
    RelayOutboxHandler,
)
from tests.unit.application.conftest import OutboxSeeder
from tests.unit.factories.handler_factories import create_relay_outbox_handler
from tests.unit.stubs.gateways import InMemoryOutboxGateway
from tests.unit.stubs.infrastructure import RecordingOutboxPublisher


async def test_publishes_pending_messages_and_marks_them_processed(
    seed_outbox: OutboxSeeder,
    outbox_gateway: InMemoryOutboxGateway,
    outbox_publisher: RecordingOutboxPublisher,
    relay_outbox_handler: RelayOutboxHandler,
) -> None:
    messages = await seed_outbox(3)

    response = await relay_outbox_handler.handle(RelayOutboxCommand())

    assert response == RelayOutboxResponse(published=3, total=3)
    assert [m.id for m in outbox_publisher.published] == [m.id for m in messages]
    assert outbox_gateway.processed == [m.id for m in messages]


async def test_a_processed_message_is_not_published_again(
    seed_outbox: OutboxSeeder,
    outbox_publisher: RecordingOutboxPublisher,
    relay_outbox_handler: RelayOutboxHandler,
) -> None:
    await seed_outbox(2)

    await relay_outbox_handler.handle(RelayOutboxCommand())
    second = await relay_outbox_handler.handle(RelayOutboxCommand())

    assert second.total == 0
    assert len(outbox_publisher.published) == 2


async def test_batch_size_caps_the_drain(
    seed_outbox: OutboxSeeder,
    outbox_gateway: InMemoryOutboxGateway,
    relay_outbox_handler: RelayOutboxHandler,
) -> None:
    await seed_outbox(5)

    response = await relay_outbox_handler.handle(RelayOutboxCommand(batch_size=2))

    assert response.published == 2
    assert len(outbox_gateway.processed) == 2


async def test_a_failing_message_does_not_block_the_ones_behind_it(
    seed_outbox: OutboxSeeder,
    outbox_gateway: InMemoryOutboxGateway,
) -> None:
    """A poisoned event must stay pending while the rest of the batch drains."""
    messages = await seed_outbox(3)
    poisoned = messages[1].id
    publisher = RecordingOutboxPublisher(failing_ids=frozenset({poisoned}))
    handler = create_relay_outbox_handler(
        outbox_gateway=outbox_gateway,
        outbox_publisher=publisher,
    )

    response = await handler.handle(RelayOutboxCommand())

    assert response == RelayOutboxResponse(published=2, total=3)
    assert poisoned not in outbox_gateway.processed
    assert [m.id for m in publisher.published] == [messages[0].id, messages[2].id]


async def test_a_failed_message_is_retried_on_the_next_tick(
    seed_outbox: OutboxSeeder,
    outbox_gateway: InMemoryOutboxGateway,
) -> None:
    messages = await seed_outbox(1)
    failing = create_relay_outbox_handler(
        outbox_gateway=outbox_gateway,
        outbox_publisher=RecordingOutboxPublisher(
            failing_ids=frozenset({messages[0].id}),
        ),
    )
    await failing.handle(RelayOutboxCommand())

    recovered_publisher = RecordingOutboxPublisher()
    recovered = create_relay_outbox_handler(
        outbox_gateway=outbox_gateway,
        outbox_publisher=recovered_publisher,
    )
    response = await recovered.handle(RelayOutboxCommand())

    assert response.published == 1
    assert [m.id for m in recovered_publisher.published] == [messages[0].id]
