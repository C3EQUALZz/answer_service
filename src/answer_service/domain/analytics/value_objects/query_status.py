from enum import StrEnum, auto


class QueryStatus(StrEnum):
    """Whether serving the query completed or raised.

    Distinct from :class:`QueryOutcome`, which says how *much* was found. A
    search that returned nothing succeeded — it is a gap in the catalog, not a
    failure of the service — and conflating the two would make the gap report
    and the error report describe each other.
    """

    SUCCEEDED = auto()
    FAILED = auto()
