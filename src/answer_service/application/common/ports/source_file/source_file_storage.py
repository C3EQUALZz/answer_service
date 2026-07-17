from abc import abstractmethod
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from answer_service.domain.indexing.value_objects.source_reference import (
        SourceReference,
    )


class SourceFileStorage(Protocol):
    """Staging storage for uploaded source files.

    The HTTP request persists the upload here and hands the background worker a
    :class:`SourceReference`; the worker later reads the bytes back.
    """

    @abstractmethod
    async def save(self, *, content: bytes, filename: str) -> SourceReference:
        raise NotImplementedError

    @abstractmethod
    async def open(self, reference: SourceReference) -> bytes:
        raise NotImplementedError
