from abc import abstractmethod
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Sequence

    from answer_service.application.common.ports.source_file.source_row import SourceRow


class SourceFileReader(Protocol):
    """Parses and validates CSV / Excel source files (implemented with polars).

    ``validate`` is a cheap, fail-fast check meant for the HTTP request: it
    confirms the bytes are a readable CSV/Excel document with the required
    columns, raising an ``InvalidSourceFileError`` otherwise. ``read_rows`` is
    the full parse, run by the background worker.
    """

    @abstractmethod
    async def validate(self, *, content: bytes, filename: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def read_rows(self, *, content: bytes) -> Sequence[SourceRow]:
        raise NotImplementedError
