"""Minimal handlers and pipelines for exercising the mediator itself.

Deliberately not the production ones: these tests are about dispatch, chaining
and ordering, so the parts being wired need to be trivial enough that a failing
assertion can only mean the mediator got it wrong.
"""

from dataclasses import dataclass
from typing import Any, Final, override

from answer_service.application.common.mediator.handlers import (
    CommandHandler,
    HandleNext,
    PipelineHandler,
    RequestHandler,
)
from answer_service.application.common.mediator.markers import Command, Query
from answer_service.domain.common.error import AppError
from answer_service.infrastructure.mediator.interfaces import Handler, Resolver
from tests.unit.stubs.infrastructure import CallJournal


class HandlerFailedError(AppError):
    """Raised by the failing handler stub."""


@dataclass(frozen=True, slots=True)
class GreetCommand(Command[str]):
    name: str


@dataclass(frozen=True, slots=True)
class FailingCommand(Command[str]):
    pass


@dataclass(frozen=True, slots=True)
class CountQuery(Query[int]):
    value: int


@dataclass(frozen=True, slots=True)
class UnregisteredCommand(Command[str]):
    pass


class GreetHandler(CommandHandler[GreetCommand, str]):
    def __init__(self, journal: CallJournal) -> None:
        self._journal: Final[CallJournal] = journal

    @override
    async def handle(self, command: GreetCommand) -> str:
        self._journal.record("handler")
        return f"hello {command.name}"


class FailingHandler(CommandHandler[FailingCommand, str]):
    def __init__(self, journal: CallJournal) -> None:
        self._journal: Final[CallJournal] = journal

    @override
    async def handle(self, command: FailingCommand) -> str:
        self._journal.record("handler")
        msg = "handler refused to run."
        raise HandlerFailedError(msg)


class CountHandler(RequestHandler[CountQuery, int]):
    @override
    async def handle(self, request: CountQuery) -> int:
        return request.value * 2


class RecordingPipeline(PipelineHandler[Any, Any]):
    """Writes its name to the journal on the way in and on the way out."""

    name: str = "pipeline"

    def __init__(self, journal: CallJournal) -> None:
        self._journal: Final[CallJournal] = journal

    @override
    async def handle(
        self,
        request: Any,
        handle_next: HandleNext[Any, Any],
    ) -> Any:
        self._journal.record(f"{self.name}:enter")
        try:
            response = await handle_next(request)
        except AppError:
            self._journal.record(f"{self.name}:error")
            raise
        self._journal.record(f"{self.name}:exit")
        return response


class OuterPipeline(RecordingPipeline):
    name = "outer"


class InnerPipeline(RecordingPipeline):
    name = "inner"


class ShortCircuitPipeline(PipelineHandler[Any, Any]):
    """Never calls the rest of the chain."""

    def __init__(self, journal: CallJournal) -> None:
        self._journal: Final[CallJournal] = journal

    @override
    async def handle(
        self,
        request: Any,
        handle_next: HandleNext[Any, Any],
    ) -> Any:
        del handle_next
        self._journal.record("short-circuit")
        return "short-circuited"


class StubResolver(Resolver):
    """Resolves from a prepared type-to-instance mapping.

    Stands in for the dishka container, which needs a running application to
    build; the mediator only ever asks a resolver for an instance by type.
    """

    def __init__(self, instances: dict[type[Any], Any]) -> None:
        self._instances = instances
        self.resolved: list[str] = []

    @override
    async def resolve[TDependency: Handler](
        self,
        dependency_type: type[TDependency],
    ) -> TDependency:
        self.resolved.append(dependency_type.__name__)
        instance: TDependency = self._instances[dependency_type]
        return instance
