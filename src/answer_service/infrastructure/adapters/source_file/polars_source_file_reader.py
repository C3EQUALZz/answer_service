import asyncio
import io
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Final, final, override

import polars as pl

from answer_service.application.common.ports.source_file.source_file_reader import (
    SourceFileReader,
)
from answer_service.application.common.ports.source_file.source_row import SourceRow
from answer_service.application.error import (
    MissingSourceColumnsError,
    UnsupportedSourceFormatError,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

logger: Final[logging.Logger] = logging.getLogger(__name__)

EXTERNAL_ID_COLUMN: Final[str] = "external_id"
QUESTION_COLUMN: Final[str] = "question"
ANSWER_COLUMN: Final[str] = "answer"
CATEGORY_COLUMN: Final[str] = "category"
UPDATED_AT_COLUMN: Final[str] = "updated_at"

REQUIRED_COLUMNS: Final[frozenset[str]] = frozenset(
    {
        EXTERNAL_ID_COLUMN,
        QUESTION_COLUMN,
        ANSWER_COLUMN,
        CATEGORY_COLUMN,
        UPDATED_AT_COLUMN,
    },
)

CSV_SUFFIXES: Final[frozenset[str]] = frozenset({".csv"})
EXCEL_SUFFIXES: Final[frozenset[str]] = frozenset({".xlsx", ".xls"})

# Modern .xlsx is a zip; legacy .xls is an OLE2 compound document.
XLSX_MAGIC: Final[bytes] = b"PK\x03\x04"
XLS_MAGIC: Final[bytes] = b"\xd0\xcf\x11\xe0"


@final
class PolarsSourceFileReader(SourceFileReader):
    """Reads CSV and Excel uploads with polars.

    ``validate`` and ``read_rows`` both parse the file. That duplication is
    deliberate: validation runs in the HTTP request to reject a broken upload
    before anything is persisted, while the full read runs minutes later in the
    worker, against bytes that were never held in memory in between.
    """

    @override
    async def validate(self, *, content: bytes, filename: str) -> None:
        frame = await asyncio.to_thread(self._parse, content, filename)
        self._ensure_columns(frame, filename)

    @override
    async def read_rows(self, *, content: bytes) -> Sequence[SourceRow]:
        frame = await asyncio.to_thread(self._parse, content, "")
        self._ensure_columns(frame, "")
        return [self._to_row(row) for row in frame.iter_rows(named=True)]

    def _parse(self, content: bytes, filename: str) -> pl.DataFrame:
        """Chooses the parser by what the bytes are, not what they are called.

        ``read_rows`` runs in the worker, which has only the stored bytes — the
        original filename never crossed the queue. Sniffing keeps both entry
        points on the same decision, so a file that validates on upload cannot
        fail to parse later.
        """
        try:
            if self._is_excel(content):
                return pl.read_excel(io.BytesIO(content))
            return pl.read_csv(io.BytesIO(content))
        except Exception as e:
            msg = f"'{filename or 'the source file'}' could not be parsed."
            raise UnsupportedSourceFormatError(msg) from e

    @staticmethod
    def _is_excel(content: bytes) -> bool:
        return content.startswith((XLSX_MAGIC, XLS_MAGIC))

    @staticmethod
    def _ensure_columns(frame: pl.DataFrame, filename: str) -> None:
        missing = REQUIRED_COLUMNS - set(frame.columns)
        if missing:
            msg = (
                f"'{filename or 'the source file'}' is missing required "
                f"column(s): {', '.join(sorted(missing))}."
            )
            raise MissingSourceColumnsError(msg)

    @staticmethod
    def _to_row(row: dict[str, object]) -> SourceRow:
        return SourceRow(
            external_id=str(row[EXTERNAL_ID_COLUMN]),
            question=str(row[QUESTION_COLUMN]),
            answer=str(row[ANSWER_COLUMN]),
            category=str(row[CATEGORY_COLUMN]),
            updated_at=PolarsSourceFileReader._to_datetime(row[UPDATED_AT_COLUMN]),
        )

    @staticmethod
    def _to_datetime(value: object) -> datetime:
        """Normalises the timestamp to an aware UTC value.

        Polars types the column as naive when the file has no offset. Storing
        that as-is would make every comparison against a stored aware timestamp
        raise, so a missing offset is read as UTC.
        """
        if isinstance(value, datetime):
            moment = value
        else:
            try:
                moment = datetime.fromisoformat(str(value))
            except ValueError as e:
                msg = f"'{value}' is not a readable timestamp."
                raise UnsupportedSourceFormatError(msg) from e

        return moment if moment.tzinfo is not None else moment.replace(tzinfo=UTC)
