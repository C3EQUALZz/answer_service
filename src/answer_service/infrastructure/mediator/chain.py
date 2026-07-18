import functools
from typing import TYPE_CHECKING, Any, cast, override

from answer_service.infrastructure.mediator.interfaces import Chain

if TYPE_CHECKING:
    from collections.abc import Iterable

    from answer_service.application.common.mediator.handlers import (
        HandleNext,
        PipelineHandler,
        RequestHandler,
    )
    from answer_service.application.common.mediator.markers import BaseRequest


class ChainImpl(Chain):
    """Wraps a handler in its pipelines, innermost last.

    Chain of Responsibility: each pipeline receives the rest of the chain as its
    ``handle_next`` and decides whether, and around what, to run.
    """

    @override
    def build_pipeline_handlers(
        self,
        handler: RequestHandler[Any, Any],
        pipeline_handlers: Iterable[PipelineHandler[Any, Any]],
    ) -> HandleNext[Any, Any]:
        """Builds the chain so the *first* pipeline given ends up outermost.

        Wrapping is applied from the inside out, so the list is consumed in
        reverse. That way registration order reads as execution order:
        ``(TransactionPipeline, EventsPipeline)`` means the transaction opens
        first and closes last, with the events drained inside it. Reading the
        registration backwards is exactly the mistake that would publish events
        after the commit and quietly break the outbox guarantee.
        """
        handle_next: HandleNext[Any, Any] = handler.handle

        for pipeline_handler in reversed(list(pipeline_handlers)):
            handle_next = self._wrap_with_pipeline(pipeline_handler, handle_next)

        return handle_next

    @staticmethod
    def _wrap_with_pipeline(
        pipeline_handler: PipelineHandler[Any, Any],
        handle_next: HandleNext[Any, Any],
    ) -> HandleNext[Any, Any]:
        @functools.wraps(handle_next)
        async def wrapped_handler[TResponse](request: BaseRequest[Any]) -> TResponse:
            return cast(
                "TResponse",
                await pipeline_handler.handle(request, handle_next),
            )

        return wrapped_handler
