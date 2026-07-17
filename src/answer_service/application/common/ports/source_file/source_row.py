from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class SourceRow:
    """A single raw row parsed from the source CSV / Excel file.

    Fields are untyped strings straight from the file; the application maps them
    to domain value objects (which validate them).
    """

    external_id: str
    question: str
    answer: str
    category: str
    updated_at: datetime
