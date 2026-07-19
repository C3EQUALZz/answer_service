from answer_service.domain.common.error import AppError


class ApplicationError(AppError):
    """Base exception class for the application layer."""


class ConversationNotFoundError(ApplicationError):
    """Raised when a requested conversation does not exist."""


class PaginationError(ApplicationError):
    """Raised when pagination parameters are invalid."""


class DuplicateInboxMessageError(ApplicationError):
    """Raised when a message with the same message_id was already processed."""


class InvalidSourceFileError(ApplicationError):
    """Raised when the uploaded source file cannot be used for synchronization."""


class UnsupportedSourceFormatError(InvalidSourceFileError):
    """Raised when the source file is neither a valid CSV nor Excel document."""


class MissingSourceColumnsError(InvalidSourceFileError):
    """Raised when the source file lacks the required columns."""


class IndexingTaskNotFoundError(ApplicationError):
    """Raised when the indexing task a worker was asked to run does not exist."""
