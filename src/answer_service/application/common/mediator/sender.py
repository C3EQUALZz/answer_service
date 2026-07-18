from abc import abstractmethod
from typing import Protocol

from .markers import BaseRequest


class Sender(Protocol):
    """Dispatches a request to its handler through the configured pipelines.

    Entry points (HTTP routes, background tasks) depend on this rather than on a
    concrete handler, so the pipeline stack — transaction boundary, event
    draining — is applied exactly once, in one place, instead of being rebuilt
    at every call site.
    """

    @abstractmethod
    async def send[TResponse](self, request: BaseRequest[TResponse]) -> TResponse:
        raise NotImplementedError
