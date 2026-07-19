"""Builders for real CSV and Excel bytes.

The reader is one of the few adapters that can be exercised for real without a
running service, so the tests feed it genuine file bytes rather than a stub.
"""

import io
from collections.abc import Iterable
from typing import Final

import polars as pl

REQUIRED_COLUMNS: Final[Iterable[str]] = (
    "external_id",
    "question",
    "answer",
    "category",
    "updated_at",
)


def make_source_frame(
    rows: int = 1,
    updated_at: str = "2026-01-01T12:00:00+00:00",
) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "external_id": [f"q-{index}" for index in range(rows)],
            "question": [f"Question {index}?" for index in range(rows)],
            "answer": [f"Answer {index}." for index in range(rows)],
            "category": ["billing" for _ in range(rows)],
            "updated_at": [updated_at for _ in range(rows)],
        },
    )


def make_csv_bytes(rows: int = 1, **kwargs: str) -> bytes:
    buffer = io.BytesIO()
    make_source_frame(rows, **kwargs).write_csv(buffer)
    return buffer.getvalue()


def make_excel_bytes(rows: int = 1, **kwargs: str) -> bytes:
    buffer = io.BytesIO()
    make_source_frame(rows, **kwargs).write_excel(buffer)
    return buffer.getvalue()


def make_csv_bytes_without(column: str) -> bytes:
    buffer = io.BytesIO()
    make_source_frame().drop(column).write_csv(buffer)
    return buffer.getvalue()
