from answer_service.domain.common.error import AppError


class ApplicationError(AppError):
    """Base exception class for the application layer."""


class ConversationNotFoundError(ApplicationError):
    """Raised when a requested conversation does not exist."""


class PaginationError(ApplicationError):
    """Raised when pagination parameters are invalid."""


class DuplicateInboxMessageError(ApplicationError):
    """Raised when a message with the same message_id was already processed."""