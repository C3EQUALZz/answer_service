import io
from datetime import UTC

import pytest

from answer_service.application.error import (
    MissingSourceColumnsError,
    UnsupportedSourceFormatError,
)
from answer_service.infrastructure.adapters.source_file import PolarsSourceFileReader
from tests.unit.factories.source_file_factories import (
    make_csv_bytes,
    make_csv_bytes_without,
    make_excel_bytes,
    make_source_frame,
)


async def test_reads_every_row_of_a_csv(reader: PolarsSourceFileReader) -> None:
    rows = await reader.read_rows(content=make_csv_bytes(rows=3))

    assert len(rows) == 3
    assert rows[0].external_id == "q-0"
    assert rows[0].question == "Question 0?"
    assert rows[0].answer == "Answer 0."
    assert rows[0].category == "billing"


async def test_reads_an_excel_file(reader: PolarsSourceFileReader) -> None:
    rows = await reader.read_rows(content=make_excel_bytes(rows=2))

    assert len(rows) == 2
    assert rows[0].external_id == "q-0"


@pytest.mark.parametrize("filename", ("faq.xlsx", "faq.XLSX", "", "no-extension"))
async def test_excel_is_recognised_regardless_of_the_filename(
    filename: str,
    reader: PolarsSourceFileReader,
) -> None:
    """The worker reads stored bytes and never sees the uploaded filename.

    Deciding the format by extension meant an Excel upload passed validation in
    the request and then failed to parse in the worker.
    """
    content = make_excel_bytes()

    await reader.validate(content=content, filename=filename)
    rows = await reader.read_rows(content=content)

    assert len(rows) == 1


async def test_a_csv_validated_on_upload_reads_back_in_the_worker(
    reader: PolarsSourceFileReader,
) -> None:
    content = make_csv_bytes(rows=2)

    await reader.validate(content=content, filename="faq.csv")

    assert len(await reader.read_rows(content=content)) == 2


async def test_a_naive_timestamp_is_read_as_utc(
    reader: PolarsSourceFileReader,
) -> None:
    """A naive value would raise on every comparison with a stored aware one."""
    rows = await reader.read_rows(
        content=make_csv_bytes(updated_at="2026-01-01T12:00:00"),
    )

    assert rows[0].updated_at.tzinfo is not None
    assert rows[0].updated_at.utcoffset() == UTC.utcoffset(None)


async def test_an_offset_timestamp_keeps_its_offset(
    reader: PolarsSourceFileReader,
) -> None:
    rows = await reader.read_rows(
        content=make_csv_bytes(updated_at="2026-01-01T12:00:00+00:00"),
    )

    assert rows[0].updated_at.tzinfo is not None


@pytest.mark.parametrize(
    "column",
    ("external_id", "question", "answer", "category", "updated_at"),
)
async def test_every_required_column_is_required(
    column: str,
    reader: PolarsSourceFileReader,
) -> None:
    content = make_csv_bytes_without(column)

    with pytest.raises(MissingSourceColumnsError, match=column):
        await reader.validate(content=content, filename="faq.csv")


async def test_a_missing_column_is_caught_on_upload_not_in_the_worker(
    reader: PolarsSourceFileReader,
) -> None:
    """Validation exists so a broken file never becomes a queued task."""
    content = make_csv_bytes_without("answer")

    with pytest.raises(MissingSourceColumnsError):
        await reader.validate(content=content, filename="f.csv")


async def test_unreadable_bytes_are_rejected(reader: PolarsSourceFileReader) -> None:
    with pytest.raises(UnsupportedSourceFormatError):
        await reader.validate(content=b"\x00\x01\x02 not a document", filename="faq.pdf")


async def test_an_empty_file_is_rejected(reader: PolarsSourceFileReader) -> None:
    with pytest.raises(UnsupportedSourceFormatError):
        await reader.validate(content=b"", filename="faq.csv")


async def test_a_header_only_file_yields_no_rows(
    reader: PolarsSourceFileReader,
) -> None:
    """An empty catalog is a legitimate sync: it deletes everything."""
    content = make_csv_bytes(rows=0)

    await reader.validate(content=content, filename="faq.csv")

    assert await reader.read_rows(content=content) == []


async def test_extra_columns_are_ignored(reader: PolarsSourceFileReader) -> None:
    """Customers add their own columns; that must not break the sync."""
    frame = make_source_frame().with_columns(note=make_source_frame()["category"])
    buffer = io.BytesIO()
    frame.write_csv(buffer)

    rows = await reader.read_rows(content=buffer.getvalue())

    assert len(rows) == 1
