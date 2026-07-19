from dataclasses import dataclass
from typing import Self, override

from answer_service.domain.analytics.errors import InconsistentQueryExecutionError
from answer_service.domain.analytics.value_objects.error_code import ErrorCode
from answer_service.domain.analytics.value_objects.query_status import QueryStatus
from answer_service.domain.common.value_object import ValueObject


@dataclass(frozen=True)
class QueryExecution(ValueObject):
    """How serving the query ended, and why if it ended badly.

    The two fields are one value because neither is meaningful alone: a failure
    with no code cannot be grouped in the report, and a code on a success
    describes nothing. Binding them here means the failure report cannot be
    asked to render a row it has no reason for.

    Positional rather than keyword-only: this is stored as a SQLAlchemy
    ``composite``, which the ORM builds by position. See ``QueryOutcome``.
    """

    status: QueryStatus
    error_code: ErrorCode | None = None

    @classmethod
    def succeeded(cls) -> Self:
        return cls(QueryStatus.SUCCEEDED)

    @classmethod
    def failed(cls, error_code: ErrorCode) -> Self:
        return cls(QueryStatus.FAILED, error_code)

    @property
    def is_failed(self) -> bool:
        return self.status is QueryStatus.FAILED

    @override
    def _validate(self) -> None:
        if self.is_failed and self.error_code is None:
            msg = "A failed query must record the error code it failed with."
            raise InconsistentQueryExecutionError(msg)
        if not self.is_failed and self.error_code is not None:
            msg = (
                f"A {self.status.value} query cannot carry an error code, "
                f"got '{self.error_code}'."
            )
            raise InconsistentQueryExecutionError(msg)
