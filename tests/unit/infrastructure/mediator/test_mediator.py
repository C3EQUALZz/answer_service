import pytest

from answer_service.application.common.mediator.markers import Command
from answer_service.infrastructure.errors import HandlerNotFoundError
from answer_service.infrastructure.mediator import MediatorImpl, Registry
from tests.unit.stubs.infrastructure import CallJournal
from tests.unit.stubs.mediator import (
    CountHandler,
    CountQuery,
    FailingCommand,
    FailingHandler,
    GreetCommand,
    GreetHandler,
    HandlerFailedError,
    InnerPipeline,
    OuterPipeline,
    ShortCircuitPipeline,
    StubResolver,
    UnregisteredCommand,
)


async def test_dispatches_to_the_registered_handler(
    mediator: MediatorImpl,
    registry: Registry,
) -> None:
    registry.add_request_handler(GreetCommand, GreetHandler)

    response = await mediator.send(GreetCommand(name="world"))

    assert response == "hello world"


async def test_raises_when_no_handler_is_registered(mediator: MediatorImpl) -> None:
    command = UnregisteredCommand()

    with pytest.raises(HandlerNotFoundError, match="UnregisteredCommand"):
        await mediator.send(command)


async def test_runs_without_pipelines(
    mediator: MediatorImpl,
    registry: Registry,
    journal: CallJournal,
) -> None:
    registry.add_request_handler(GreetCommand, GreetHandler)

    await mediator.send(GreetCommand(name="world"))

    assert journal.entries == ["handler"]


async def test_the_first_registered_pipeline_is_the_outermost(
    mediator: MediatorImpl,
    registry: Registry,
    journal: CallJournal,
) -> None:
    """Registration order reads as execution order.

    Getting this backwards is what would put the transaction *inside* the event
    draining, publishing events after the commit and losing the outbox's
    all-or-nothing guarantee.
    """
    registry.add_request_handler(GreetCommand, GreetHandler)
    registry.add_pipeline_handlers(Command, OuterPipeline, InnerPipeline)

    await mediator.send(GreetCommand(name="world"))

    assert journal.entries == [
        "outer:enter",
        "inner:enter",
        "handler",
        "inner:exit",
        "outer:exit",
    ]


async def test_a_failure_unwinds_the_pipelines_outwards(
    mediator: MediatorImpl,
    registry: Registry,
    journal: CallJournal,
) -> None:
    registry.add_request_handler(FailingCommand, FailingHandler)
    registry.add_pipeline_handlers(Command, OuterPipeline, InnerPipeline)

    command = FailingCommand()

    with pytest.raises(HandlerFailedError):
        await mediator.send(command)

    assert journal.entries == [
        "outer:enter",
        "inner:enter",
        "handler",
        "inner:error",
        "outer:error",
    ]


async def test_a_pipeline_can_stop_the_chain(
    mediator: MediatorImpl,
    registry: Registry,
    journal: CallJournal,
) -> None:
    """A pipeline that never calls handle_next must keep the handler from running."""
    registry.add_request_handler(GreetCommand, GreetHandler)
    registry.add_pipeline_handlers(Command, ShortCircuitPipeline, InnerPipeline)

    response = await mediator.send(GreetCommand(name="world"))

    assert response == "short-circuited"
    assert journal.entries == ["short-circuit"]


async def test_queries_bypass_the_command_pipelines(
    mediator: MediatorImpl,
    registry: Registry,
    journal: CallJournal,
) -> None:
    registry.add_request_handler(CountQuery, CountHandler)
    registry.add_pipeline_handlers(Command, OuterPipeline)

    response = await mediator.send(CountQuery(value=21))

    assert response == 42
    assert journal.entries == []


async def test_handlers_are_resolved_per_dispatch(
    mediator: MediatorImpl,
    registry: Registry,
    resolver: StubResolver,
) -> None:
    """A cached handler would leak one request's session into the next."""
    registry.add_request_handler(GreetCommand, GreetHandler)
    registry.add_pipeline_handlers(Command, OuterPipeline)

    await mediator.send(GreetCommand(name="a"))
    await mediator.send(GreetCommand(name="b"))

    assert resolver.resolved == [
        "GreetHandler",
        "OuterPipeline",
        "GreetHandler",
        "OuterPipeline",
    ]
