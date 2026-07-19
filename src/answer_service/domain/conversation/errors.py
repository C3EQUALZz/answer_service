from answer_service.domain.common.error import DomainError, DomainFieldError


class ConversationDomainError(DomainError):
    """Base error for the conversation domain."""


class EmptyAnswerError(DomainFieldError):
    """Raised when a generated answer has no content."""


class UngroundedAnswerError(ConversationDomainError):
    """Raised when an answer is produced without a source to attribute it to."""
