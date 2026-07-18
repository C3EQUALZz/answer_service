from abc import ABC, abstractmethod
from typing import Any

from answer_service.application.common.mediator.handlers import (
    PipelineHandler,
    RequestHandler,
)

type Handler = RequestHandler[Any, Any] | PipelineHandler[Any, Any]


class Resolver(ABC):
    """Fetches handler instances from the dependency container."""

    @abstractmethod
    async def resolve[TDependency: Handler](
        self,
        dependency_type: type[TDependency],
    ) -> TDependency: ...
