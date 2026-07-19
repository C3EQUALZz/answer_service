import logging
from typing import Final, override

from answer_service.application.commands.outbox.relay_outbox.command import (
    RelayOutboxCommand,
    RelayOutboxResponse,
)
from answer_service.application.common.mediator.handlers import CommandHandler
from answer_service.application.common.ports.outbox import (
    OutboxCommandGateway,
    OutboxPublisher,
)
from answer_service.domain.common.error import AppError

logger: Final[logging.Logger] = logging.getLogger(__name__)


class RelayOutboxHandler(CommandHandler[RelayOutboxCommand, RelayOutboxResponse]):
    """Publishes pending outbox messages to the broker.

    Delivery is at-least-once: a message is marked processed only after its
    publish returns, so a crash between the two re-sends it on the next tick.
    Consumers must therefore be idempotent — they key off ``OutboxMessage.id``,
    which is stable across retries.

    A message that fails to publish is logged and skipped rather than aborting
    the batch, so one poisoned event cannot block the queue behind it. Its row
    stays unmarked and is retried on the next tick.

    Relies on the transaction pipeline for its unit of work: the row locks taken
    by ``read_pending`` must be held until the ``mark_processed`` writes commit.
    """

    def __init__(
        self,
        outbox_command_gateway: OutboxCommandGateway,
        outbox_publisher: OutboxPublisher,
    ) -> None:
        self._outbox_command_gateway: Final[OutboxCommandGateway] = outbox_command_gateway
        self._outbox_publisher: Final[OutboxPublisher] = outbox_publisher

    @override
    async def handle(self, command: RelayOutboxCommand) -> RelayOutboxResponse:
        messages = await self._outbox_command_gateway.read_pending(
            limit=command.batch_size,
        )
        if not messages:
            logger.debug("relay_outbox: nothing pending")
            return RelayOutboxResponse(published=0, total=0)

        logger.info(
            "relay_outbox: %d pending message(s), batch size %d",
            len(messages),
            command.batch_size,
        )
        published = 0

        for message in messages:
            try:
                await self._outbox_publisher.publish(message)
            except AppError:
                logger.exception(
                    "relay_outbox: failed to publish message id=%s type=%s",
                    message.id,
                    message.event_type,
                )
                continue

            await self._outbox_command_gateway.mark_processed(message.id)
            published += 1
            logger.debug(
                "relay_outbox: published %s (id=%s)",
                message.event_type,
                message.id,
            )

        logger.info(
            "relay_outbox: published=%d / total=%d",
            published,
            len(messages),
        )
        return RelayOutboxResponse(published=published, total=len(messages))
