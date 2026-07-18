"""Stand-ins for the source-file ports.

The reader is driven by whatever rows a test hands it, so the tests exercise the
sync logic without parsing real CSV/Excel bytes.
"""

from collections.abc import Sequence
from typing import final, override

from answer_service.application.common.ports.source_file.source_file_reader import (
    SourceFileReader,
)
from answer_service.application.common.ports.source_file.source_file_storage import (
    SourceFileStorage,
)
from answer_service.application.common.ports.source_file.source_row import SourceRow
from answer_service.application.error import UnsupportedSourceFormatError
from answer_service.domain.indexing.value_objects.source_reference import SourceReference


@final
class StubSourceFileStorage(SourceFileStorage):
    def __init__(self, reference: SourceReference) -> None:
        self._reference = reference
        self.saved: list[bytes] = []
        self.opened: list[SourceReference] = []

    @override
    async def save(self, *, content: bytes, filename: str) -> SourceReference:
        del filename
        self.saved.append(content)
        return self._reference

    @override
    async def open(self, reference: SourceReference) -> bytes:
        self.opened.append(reference)
        return b"stub-source-bytes"


@final
class StubSourceFileReader(SourceFileReader):
    """Returns preset rows; optionally rejects the upload in ``validate``."""

    def __init__(
        self,
        rows: Sequence[SourceRow] = (),
        *,
        rejects: bool = False,
    ) -> None:
        self._rows = rows
        self._rejects = rejects
        self.validated: list[str] = []

    @override
    async def validate(self, *, content: bytes, filename: str) -> None:
        del content
        self.validated.append(filename)
        if self._rejects:
            msg = f"'{filename}' is not a supported source file."
            raise UnsupportedSourceFormatError(msg)

    @override
    async def read_rows(self, *, content: bytes) -> Sequence[SourceRow]:
        del content
        return self._rows
