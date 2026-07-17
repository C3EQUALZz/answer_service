from answer_service.domain.common.error import DomainError, DomainFieldError


class SearchDomainError(DomainError):
    """Base error for the search domain."""


class EmptySearchQueryError(DomainFieldError):
    """Raised when a search query is empty."""


class SearchQueryTooLongError(DomainFieldError):
    """Raised when a search query exceeds the maximum allowed length."""


class TopKOutOfRangeError(DomainFieldError):
    """Raised when top_k is outside the allowed range."""


class EmptyCategoryFilterError(DomainFieldError):
    """Raised when a category filter is empty."""


class InvalidScoreError(DomainFieldError):
    """Raised when a score is not a finite number."""


class InvalidRankError(DomainFieldError):
    """Raised when a result rank is not a positive integer."""
