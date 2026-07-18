from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from answer_service.application.common.mediator.handlers import (
        PipelineHandler,
        RequestHandler,
    )
    from answer_service.application.common.mediator.markers import BaseRequest


class Registry:
    """Maps request types to their handler and their pipelines."""

    def __init__(self) -> None:
        self._request_handlers: Final[
            dict[type[BaseRequest[Any]], type[RequestHandler[Any, Any]]]
        ] = {}
        self._pipeline_handlers: Final[
            dict[type[BaseRequest[Any]], list[type[PipelineHandler[Any, Any]]]]
        ] = {}

    def add_request_handler(
        self,
        request_type: type[BaseRequest[Any]],
        request_handler: type[RequestHandler[Any, Any]],
    ) -> None:
        """Binds one handler to one request type."""
        self._request_handlers[request_type] = request_handler

    def add_pipeline_handlers(
        self,
        request_type: type[BaseRequest[Any]],
        *pipeline_handlers: type[PipelineHandler[Any, Any]],
    ) -> None:
        """Registers pipelines for a request type and everything below it.

        Registering against a marker such as ``Command`` covers every command at
        once, which is how the transaction and event pipelines get applied
        without naming each command — and, more importantly, without a new
        command silently escaping them.
        """
        self._pipeline_handlers.setdefault(request_type, []).extend(pipeline_handlers)

    def get_request_handler(
        self,
        request_type: type[BaseRequest[Any]],
    ) -> type[RequestHandler[Any, Any]] | None:
        """Returns the handler bound to *request_type*, if any."""
        return self._request_handlers.get(request_type)

    def get_pipeline_handlers(
        self,
        request_type: type[BaseRequest[Any]],
    ) -> list[type[PipelineHandler[Any, Any]]]:
        """Returns every pipeline registered for *request_type* or a base of it."""
        return [
            pipeline_handler
            for registered_type, pipeline_handlers in self._pipeline_handlers.items()
            if issubclass(request_type, registered_type)
            for pipeline_handler in pipeline_handlers
        ]
