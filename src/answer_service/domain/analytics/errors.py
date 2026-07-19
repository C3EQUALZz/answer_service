from answer_service.domain.common.error import DomainError, DomainFieldError


class AnalyticsDomainError(DomainError):
    """Base error for the analytics domain."""


class EmptyQueryTextError(DomainFieldError):
    """Raised when a logged query has no text."""


class QueryTextTooLongError(DomainFieldError):
    """Raised when a logged query exceeds the maximum stored length."""


class NegativeResultsCountError(DomainFieldError):
    """Raised when a results count is negative."""


class NegativeLatencyError(DomainFieldError):
    """Raised when a measured latency is negative."""


class InvalidPeriodError(DomainFieldError):
    """Raised when a reporting period ends before it starts."""


class EmptyCategoryLabelError(DomainFieldError):
    """Raised when a category label is empty."""


class EmptyErrorCodeError(DomainFieldError):
    """Raised when a recorded failure carries a blank error code."""


class InconsistentQueryExecutionError(DomainFieldError):
    """Raised when a query's status and its error code contradict each other."""
