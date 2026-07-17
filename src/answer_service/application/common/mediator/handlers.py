from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import Any

from answer_service.domain.common.event import Event

from .markers import BaseRequest

type HandleNext[TRequest: BaseRequest | Event, TResponse] = Callable[
    [TRequest], Awaitable[TResponse]
]


class RequestHandler[TRequest: BaseRequest[Any], TResponse](ABC):
    @abstractmethod
    async def handle(self, request: TRequest) -> TResponse: ...


class PipelineHandler[TRequest: BaseRequest[Any] | Event, TResponse](ABC):
    @abstractmethod
    async def handle(
            self, request: TRequest, handle_next: HandleNext[TRequest, TResponse]
    ) -> TResponse: ...


class CommandHandler[TRequest: BaseRequest[Any], TResponse](
    RequestHandler[TRequest, TResponse]
):
    @abstractmethod
    async def handle(self, command: TRequest) -> TResponse: ...


class QueryHandler[TRequest: BaseRequest[Any], TResponse](
    RequestHandler[TRequest, TResponse]
):
    @abstractmethod
    async def handle(self, query: TRequest) -> TResponse: ...
