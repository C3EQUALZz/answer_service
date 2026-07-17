from answer_service.domain.common.error import DomainError, DomainFieldError


class IndexingDomainError(DomainError):
    """Base error for the indexing domain."""


class InvalidTaskTransitionError(IndexingDomainError):
    """Raised when an indexing task transition violates its state machine."""


class EmptyExternalIdError(DomainFieldError):
    """Raised when an external id is empty."""


class EmptyQuestionError(DomainFieldError):
    """Raised when a question is empty."""


class QuestionTooLongError(DomainFieldError):
    """Raised when a question exceeds the maximum allowed length."""


class EmptyAnswerError(DomainFieldError):
    """Raised when an answer is empty."""


class AnswerTooLongError(DomainFieldError):
    """Raised when an answer exceeds the maximum allowed length."""


class EmptyCategoryError(DomainFieldError):
    """Raised when a category is empty."""


class InvalidContentHashError(DomainFieldError):
    """Raised when a content hash is not a valid digest."""


class NegativeSyncCountError(DomainFieldError):
    """Raised when a synchronization counter is negative."""


class EmptyFailureCodeError(DomainFieldError):
    """Raised when a failure code is empty."""
