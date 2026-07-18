from answer_service.domain.common.error import AppError


class InfrastructureError(AppError):
    """Base exception class for the infrastructure layer."""


class UnregisteredTaskError(InfrastructureError):
    """Raised when scheduling a task whose name the broker does not know."""


class OutboxPublishError(InfrastructureError):
    """Raised when an outbox message could not be handed to its transport."""


class RepoError(InfrastructureError):
    """Raised when a persistence gateway fails to execute a statement."""


class SearchIndexError(InfrastructureError):
    """Raised when the vector store rejects a read or a write."""
