import logging
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Final

import pydantic
from fastapi import FastAPI, status
from fastapi.encoders import jsonable_encoder
from fastapi.requests import Request
from fastapi.responses import JSONResponse

from answer_service.application.error import (
    ApplicationError,
    ConversationNotFoundError,
    DuplicateInboxMessageError,
    IndexingTaskNotFoundError,
    InvalidSourceFileError,
    MissingSourceColumnsError,
    PaginationError,
    UnsupportedSourceFormatError,
)
from answer_service.domain.analytics.errors import (
    AnalyticsDomainError,
    EmptyCategoryLabelError,
    EmptyQueryTextError,
    InvalidPeriodError,
    NegativeLatencyError,
    NegativeResultsCountError,
    QueryTextTooLongError,
)
from answer_service.domain.common.error import (
    AppError,
    DomainError,
    DomainFieldError,
    InconsistentTimeError,
)
from answer_service.domain.indexing.errors import (
    AnswerTooLongError,
    DuplicateExternalIdError,
    EmptyAnswerError,
    EmptyCategoryError,
    EmptyExternalIdError,
    EmptyFailureCodeError,
    EmptyQuestionError,
    EmptySourceReferenceError,
    IndexingDomainError,
    InvalidContentHashError,
    InvalidTaskTransitionError,
    NegativeSyncCountError,
    QuestionTooLongError,
)
from answer_service.domain.search.errors import (
    EmptyCategoryFilterError,
    EmptySearchQueryError,
    InvalidRankError,
    InvalidScoreError,
    SearchDomainError,
    SearchQueryTooLongError,
    TopKOutOfRangeError,
)
from answer_service.infrastructure.errors import (
    HandlerNotFoundError,
    InfrastructureError,
    OutboxPublishError,
    RepoError,
    SearchIndexError,
    SourceFileStorageError,
    UnregisteredTaskError,
)

logger: Final[logging.Logger] = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ExceptionSchema:
    description: str


@dataclass(frozen=True, slots=True)
class ExceptionSchemaRich:
    description: str
    details: list[dict[str, Any]] | None = None


class ExceptionHandler:
    """Maps every error the service can raise onto a status code.

    Exhaustive by design. The lookup is by exact type, so an error missing from
    the table answers 500 — listing each one is what makes the choice explicit
    rather than inherited by accident from whichever base happens to match
    first. Adding an error and forgetting it here shows up in production as a
    500, not as a plausible-looking 400.
    """

    _ERROR_MAPPING: Final[MappingProxyType[type[Exception], int]] = MappingProxyType(
        {
            DomainFieldError: status.HTTP_400_BAD_REQUEST,
            InconsistentTimeError: status.HTTP_400_BAD_REQUEST,
            EmptyExternalIdError: status.HTTP_400_BAD_REQUEST,
            EmptyQuestionError: status.HTTP_400_BAD_REQUEST,
            QuestionTooLongError: status.HTTP_400_BAD_REQUEST,
            EmptyAnswerError: status.HTTP_400_BAD_REQUEST,
            AnswerTooLongError: status.HTTP_400_BAD_REQUEST,
            EmptyCategoryError: status.HTTP_400_BAD_REQUEST,
            InvalidContentHashError: status.HTTP_400_BAD_REQUEST,
            NegativeSyncCountError: status.HTTP_400_BAD_REQUEST,
            EmptyFailureCodeError: status.HTTP_400_BAD_REQUEST,
            EmptySourceReferenceError: status.HTTP_400_BAD_REQUEST,
            EmptySearchQueryError: status.HTTP_400_BAD_REQUEST,
            SearchQueryTooLongError: status.HTTP_400_BAD_REQUEST,
            TopKOutOfRangeError: status.HTTP_400_BAD_REQUEST,
            EmptyCategoryFilterError: status.HTTP_400_BAD_REQUEST,
            InvalidScoreError: status.HTTP_400_BAD_REQUEST,
            InvalidRankError: status.HTTP_400_BAD_REQUEST,
            EmptyQueryTextError: status.HTTP_400_BAD_REQUEST,
            QueryTextTooLongError: status.HTTP_400_BAD_REQUEST,
            NegativeResultsCountError: status.HTTP_400_BAD_REQUEST,
            NegativeLatencyError: status.HTTP_400_BAD_REQUEST,
            InvalidPeriodError: status.HTTP_400_BAD_REQUEST,
            EmptyCategoryLabelError: status.HTTP_400_BAD_REQUEST,
            IndexingTaskNotFoundError: status.HTTP_404_NOT_FOUND,
            ConversationNotFoundError: status.HTTP_404_NOT_FOUND,
            InvalidTaskTransitionError: status.HTTP_409_CONFLICT,
            DuplicateInboxMessageError: status.HTTP_409_CONFLICT,
            DuplicateExternalIdError: status.HTTP_409_CONFLICT,
            UnsupportedSourceFormatError: status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            pydantic.ValidationError: status.HTTP_422_UNPROCESSABLE_CONTENT,
            PaginationError: status.HTTP_422_UNPROCESSABLE_CONTENT,
            InvalidSourceFileError: status.HTTP_422_UNPROCESSABLE_CONTENT,
            MissingSourceColumnsError: status.HTTP_422_UNPROCESSABLE_CONTENT,
            AppError: status.HTTP_500_INTERNAL_SERVER_ERROR,
            DomainError: status.HTTP_500_INTERNAL_SERVER_ERROR,
            IndexingDomainError: status.HTTP_500_INTERNAL_SERVER_ERROR,
            SearchDomainError: status.HTTP_500_INTERNAL_SERVER_ERROR,
            AnalyticsDomainError: status.HTTP_500_INTERNAL_SERVER_ERROR,
            ApplicationError: status.HTTP_500_INTERNAL_SERVER_ERROR,
            InfrastructureError: status.HTTP_500_INTERNAL_SERVER_ERROR,
            HandlerNotFoundError: status.HTTP_500_INTERNAL_SERVER_ERROR,
            UnregisteredTaskError: status.HTTP_500_INTERNAL_SERVER_ERROR,
            Exception: status.HTTP_500_INTERNAL_SERVER_ERROR,
            RepoError: status.HTTP_503_SERVICE_UNAVAILABLE,
            SearchIndexError: status.HTTP_503_SERVICE_UNAVAILABLE,
            OutboxPublishError: status.HTTP_503_SERVICE_UNAVAILABLE,
            SourceFileStorageError: status.HTTP_503_SERVICE_UNAVAILABLE,
        },
    )

    def __init__(self, app: FastAPI) -> None:
        self._app: Final[FastAPI] = app
        self._status_internal_server_error: Final[int] = 500

    async def _handle(self, _: Request, exc: Exception) -> JSONResponse:
        status_code: int = self._ERROR_MAPPING.get(
            type(exc),
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

        response: ExceptionSchema | ExceptionSchemaRich
        if isinstance(exc, pydantic.ValidationError):
            response = ExceptionSchemaRich(str(exc), jsonable_encoder(exc.errors()))

        elif status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
            message_if_unavailable: str = (
                "Service temporarily unavailable. Please try again later."
            )
            response = ExceptionSchema(message_if_unavailable)

        else:
            message: str = (
                str(exc)
                if status_code < self._status_internal_server_error
                else "Internal server error."
            )
            response = ExceptionSchema(message)

        if status_code >= self._status_internal_server_error:
            logger.error(
                "exception: %s answered %d: %s",
                type(exc).__name__,
                status_code,
                exc,
                exc_info=exc,
            )
        else:
            logger.warning(
                "exception: %s answered %d: %s",
                type(exc).__name__,
                status_code,
                exc,
            )

        return JSONResponse(
            status_code=status_code,
            content=jsonable_encoder(response),
        )

    def setup_handlers(self) -> None:
        for exc_class in self._ERROR_MAPPING:
            self._app.add_exception_handler(exc_class, self._handle)
        self._app.add_exception_handler(Exception, self._handle)
