from answer_service.application.common.mediator.markers import BaseRequest, Command, Query
from answer_service.infrastructure.mediator import Registry
from tests.unit.stubs.mediator import (
    CountHandler,
    CountQuery,
    GreetCommand,
    GreetHandler,
    InnerPipeline,
    OuterPipeline,
    UnregisteredCommand,
)


def test_returns_the_handler_bound_to_a_request(registry: Registry) -> None:
    registry.add_request_handler(GreetCommand, GreetHandler)

    assert registry.get_request_handler(GreetCommand) is GreetHandler


def test_returns_nothing_for_an_unregistered_request(registry: Registry) -> None:
    assert registry.get_request_handler(UnregisteredCommand) is None


def test_a_pipeline_on_a_marker_covers_every_request_below_it(
    registry: Registry,
) -> None:
    """This is what stops a newly added command from escaping the pipelines."""
    registry.add_pipeline_handlers(Command, OuterPipeline)

    assert registry.get_pipeline_handlers(GreetCommand) == [OuterPipeline]


def test_a_pipeline_registered_for_commands_does_not_reach_queries(
    registry: Registry,
) -> None:
    """Queries do not mutate state, so they must not open a transaction."""
    registry.add_pipeline_handlers(Command, OuterPipeline)

    assert registry.get_pipeline_handlers(CountQuery) == []


def test_pipelines_on_a_base_and_on_a_request_are_combined(
    registry: Registry,
) -> None:
    registry.add_pipeline_handlers(Command, OuterPipeline)
    registry.add_pipeline_handlers(GreetCommand, InnerPipeline)

    assert set(registry.get_pipeline_handlers(GreetCommand)) == {
        OuterPipeline,
        InnerPipeline,
    }


def test_registration_order_is_preserved(registry: Registry) -> None:
    """The chain builds from this order, so it is part of the contract."""
    registry.add_pipeline_handlers(Command, OuterPipeline, InnerPipeline)

    assert registry.get_pipeline_handlers(GreetCommand) == [
        OuterPipeline,
        InnerPipeline,
    ]


def test_a_pipeline_on_the_root_marker_covers_commands_and_queries(
    registry: Registry,
) -> None:
    registry.add_pipeline_handlers(BaseRequest, OuterPipeline)

    assert registry.get_pipeline_handlers(GreetCommand) == [OuterPipeline]
    assert registry.get_pipeline_handlers(CountQuery) == [OuterPipeline]


def test_queries_get_their_own_handler(registry: Registry) -> None:
    registry.add_request_handler(CountQuery, CountHandler)

    assert registry.get_request_handler(CountQuery) is CountHandler
    assert issubclass(CountQuery, Query)
