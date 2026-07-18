from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable

    from answer_service.application.common.mediator.handlers import (
        HandleNext,
        PipelineHandler,
        RequestHandler,
    )


class Chain(ABC):
    """Builds the call chain a request travels through."""

    @abstractmethod
    def build_pipeline_handlers(
        self,
        handler: RequestHandler[Any, Any],
        pipeline_handlers: Iterable[PipelineHandler[Any, Any]],
    ) -> HandleNext[Any, Any]: ...
