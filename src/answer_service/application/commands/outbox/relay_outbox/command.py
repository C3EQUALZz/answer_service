from dataclasses import dataclass, field
from typing import Final

from answer_service.application.common.mediator.markers import Command

DEFAULT_BATCH_SIZE: Final[int] = 100


@dataclass(frozen=True, slots=True)
class RelayOutboxResponse:
    """Outcome of one relay tick, for the worker log."""

    published: int
    total: int


@dataclass(frozen=True, slots=True)
class RelayOutboxCommand(Command[RelayOutboxResponse]):
    """Drain a batch of pending outbox messages to the broker.

    Dispatched by the scheduler on a cron tick. Safe to run on several worker
    replicas at once — the gateway claims rows with ``SKIP LOCKED``.
    """

    batch_size: int = field(default=DEFAULT_BATCH_SIZE)
