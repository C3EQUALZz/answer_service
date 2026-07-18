import logging
from typing import Final, override

from answer_service.application.common.mediator.markers import BaseRequest
from answer_service.application.common.mediator.sender import Sender
from answer_service.infrastructure.errors import HandlerNotFoundError
from answer_service.infrastructure.mediator.interfaces import Chain, Resolver
from answer_service.infrastructure.mediator.registry import Registry

logger: Final[logging.Logger] = logging.getLogger(__name__)


class MediatorImpl(Sender):
    """Dispatches a request to its handler through the registered pipelines.

    Handlers and pipelines are resolved per request rather than held as
    instances: they depend on request-scoped things — the session, the events
    collection — so a cached handler would serve one request's state to the
    next.

    Only ``send`` is implemented. Domain events do not travel through an
    in-process notification bus here; they go to the outbox and reach their
    consumers as background tasks, which is what makes them survive a crash
    between the state change and its projection.
    """

    def __init__(self, resolver: Resolver, registry: Registry, chain: Chain) -> None:
        self._resolver: Final[Resolver] = resolver
        self._registry: Final[Registry] = registry
        self._chain: Final[Chain] = chain

    @override
    async def send[TResponse](self, request: BaseRequest[TResponse]) -> TResponse:
        request_type = type(request)

        handler_type = self._registry.get_request_handler(request_type)
        if handler_type is None:
            msg = f"No handler registered for '{request_type.__name__}'."
            raise HandlerNotFoundError(msg)

        request_handler = await self._resolver.resolve(handler_type)

        pipeline_handlers = [
            await self._resolver.resolve(pipeline_type)
            for pipeline_type in self._registry.get_pipeline_handlers(request_type)
        ]

        handle_next = self._chain.build_pipeline_handlers(
            request_handler,
            pipeline_handlers,
        )

        logger.debug(
            "Dispatching %s through %d pipeline(s)",
            request_type.__name__,
            len(pipeline_handlers),
        )

        response: TResponse = await handle_next(request)
        return response
