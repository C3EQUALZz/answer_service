from collections.abc import Callable
from typing import Any

import pytest

from answer_service.infrastructure.mediator import ChainImpl, MediatorImpl, Registry
from tests.unit.stubs.infrastructure import CallJournal
from tests.unit.stubs.mediator import (
    CountHandler,
    FailingHandler,
    GreetHandler,
    InnerPipeline,
    OuterPipeline,
    ShortCircuitPipeline,
    StubResolver,
)

type MediatorBuilder = Callable[[], MediatorImpl]


@pytest.fixture()
def journal() -> CallJournal:
    return CallJournal()


@pytest.fixture()
def registry() -> Registry:
    return Registry()


@pytest.fixture()
def chain() -> ChainImpl:
    return ChainImpl()


@pytest.fixture()
def instances(journal: CallJournal) -> dict[type[Any], Any]:
    """One instance per handler type, all sharing the journal."""
    return {
        GreetHandler: GreetHandler(journal),
        FailingHandler: FailingHandler(journal),
        CountHandler: CountHandler(),
        OuterPipeline: OuterPipeline(journal),
        InnerPipeline: InnerPipeline(journal),
        ShortCircuitPipeline: ShortCircuitPipeline(journal),
    }


@pytest.fixture()
def resolver(instances: dict[type[Any], Any]) -> StubResolver:
    return StubResolver(instances)


@pytest.fixture()
def mediator(
    resolver: StubResolver,
    registry: Registry,
    chain: ChainImpl,
) -> MediatorImpl:
    return MediatorImpl(resolver, registry, chain)
