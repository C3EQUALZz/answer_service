from enum import StrEnum, auto


class QueryKind(StrEnum):
    """Which entry point produced the query."""

    SEARCH = auto()
    ASK = auto()
