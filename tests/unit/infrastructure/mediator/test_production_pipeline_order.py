"""The mediator wired with the real pipelines, not stand-ins.

The chain tests prove the mediator orders pipelines as registered. This one
proves the registration we intend to ship produces the ordering the outbox
pattern actually requires: events drained and written inside the transaction
that made the state change, never after it committed.
"""

from collections import deque
from typing import Any

import pytest

from answer_service.application.common.mediator.markers import Command
from answer_service.application.pipelines.events_pipeline import EventsPipeline
from answer_service.application.pipelines.transaction_pipeline import (
    TransactionPipeline,
)
from answer_service.domain.common.events_collection import EventsCollection
from answer_service.infrastructure.mediator import ChainImpl, MediatorImpl, Registry
from tests.unit.stubs.infrastructure import (
    CallJournal,
    RecordingEventBus,
    RecordingTransactionManager,
)
from tests.unit.stubs.mediator import (
    FailingCommand,
    FailingHandler,
    GreetCommand,
    GreetHandler,
    HandlerFailedError,
    StubResolver,
)


def build_mediator(journal: CallJournal) -> tuple[MediatorImpl, Registry]:
    events_collection = EventsCollection(events=deque())
    instances: dict[type[Any], Any] = {
        GreetHandler: GreetHandler(journal),
        FailingHandler: FailingHandler(journal),
        TransactionPipeline: TransactionPipeline(
            RecordingTransactionManager(journal),
        ),
        EventsPipeline: EventsPipeline(
            events_collection,
            RecordingEventBus(journal),
        ),
    }
    registry = Registry()
    registry.add_pipeline_handlers(Command, TransactionPipeline, EventsPipeline)
    return MediatorImpl(StubResolver(instances), registry, ChainImpl()), registry


async def test_events_are_published_inside_the_transaction() -> None:
    journal = CallJournal()
    mediator, registry = build_mediator(journal)
    registry.add_request_handler(GreetCommand, GreetHandler)

    await mediator.send(GreetCommand(name="world"))

    assert journal.entries == ["handler", "publish", "commit"]


async def test_a_failure_rolls_back_without_publishing() -> None:
    journal = CallJournal()
    mediator, registry = build_mediator(journal)
    registry.add_request_handler(FailingCommand, FailingHandler)

    with pytest.raises(HandlerFailedError):
        await mediator.send(FailingCommand())

    assert journal.entries == ["handler", "rollback"]
    assert "publish" not in journal.entries
