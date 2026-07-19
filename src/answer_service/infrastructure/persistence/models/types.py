from typing import Any, override

from sqlalchemy import Integer, Text, TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Dialect

from answer_service.domain.analytics.value_objects.category_label import CategoryLabel
from answer_service.domain.analytics.value_objects.error_code import ErrorCode
from answer_service.domain.analytics.value_objects.latency import Latency
from answer_service.domain.analytics.value_objects.query_kind import QueryKind
from answer_service.domain.analytics.value_objects.query_status import QueryStatus
from answer_service.domain.analytics.value_objects.query_text import QueryText
from answer_service.domain.indexing.value_objects.answer import Answer
from answer_service.domain.indexing.value_objects.category import Category
from answer_service.domain.indexing.value_objects.external_id import ExternalId
from answer_service.domain.indexing.value_objects.failure_info import FailureInfo
from answer_service.domain.indexing.value_objects.question import Question
from answer_service.domain.indexing.value_objects.source_reference import SourceReference
from answer_service.domain.indexing.value_objects.sync_stats import SyncStats
from answer_service.domain.indexing.value_objects.task_status import IndexingTaskStatus


class ExternalIdType(TypeDecorator[ExternalId]):
    """Persists the source-provided ExternalId as plain TEXT."""

    impl = Text
    cache_ok = True

    @override
    def process_bind_param(
        self,
        value: ExternalId | None,
        dialect: Dialect,
    ) -> str | None:
        return value.value if value is not None else None

    @override
    def process_result_value(
        self,
        value: str | None,
        dialect: Dialect,
    ) -> ExternalId | None:
        return ExternalId(value=value) if value is not None else None


class QuestionType(TypeDecorator[Question]):
    """Persists Question VO as plain TEXT."""

    impl = Text
    cache_ok = True

    @override
    def process_bind_param(self, value: Question | None, dialect: Dialect) -> str | None:
        return value.content if value is not None else None

    @override
    def process_result_value(
        self,
        value: str | None,
        dialect: Dialect,
    ) -> Question | None:
        return Question(content=value) if value is not None else None


class AnswerType(TypeDecorator[Answer]):
    """Persists Answer VO as plain TEXT."""

    impl = Text
    cache_ok = True

    @override
    def process_bind_param(self, value: Answer | None, dialect: Dialect) -> str | None:
        return value.content if value is not None else None

    @override
    def process_result_value(self, value: str | None, dialect: Dialect) -> Answer | None:
        return Answer(content=value) if value is not None else None


class CategoryType(TypeDecorator[Category]):
    """Persists Category VO as plain TEXT."""

    impl = Text
    cache_ok = True

    @override
    def process_bind_param(self, value: Category | None, dialect: Dialect) -> str | None:
        return value.value if value is not None else None

    @override
    def process_result_value(
        self,
        value: str | None,
        dialect: Dialect,
    ) -> Category | None:
        return Category(value=value) if value is not None else None


class SourceReferenceType(TypeDecorator[SourceReference]):
    """Persists the storage key of the synced source file as plain TEXT."""

    impl = Text
    cache_ok = True

    @override
    def process_bind_param(
        self,
        value: SourceReference | None,
        dialect: Dialect,
    ) -> str | None:
        return value.value if value is not None else None

    @override
    def process_result_value(
        self,
        value: str | None,
        dialect: Dialect,
    ) -> SourceReference | None:
        return SourceReference(value=value) if value is not None else None


class SyncStatsType(TypeDecorator[SyncStats]):
    """Persists the run counters as JSONB.

    They are read back whole with the task and never filtered on individually,
    so one column beats four — adding a counter does not cost a migration.
    """

    impl = JSONB
    cache_ok = True

    @override
    def process_bind_param(
        self,
        value: SyncStats | None,
        dialect: Dialect,
    ) -> dict[str, Any] | None:
        if value is None:
            return None
        return {
            "created": value.created,
            "updated": value.updated,
            "deleted": value.deleted,
            "skipped": value.skipped,
        }

    @override
    def process_result_value(
        self,
        value: dict[str, Any] | None,
        dialect: Dialect,
    ) -> SyncStats | None:
        if value is None:
            return None
        return SyncStats(
            created=value["created"],
            updated=value["updated"],
            deleted=value["deleted"],
            skipped=value["skipped"],
        )


class FailureInfoType(TypeDecorator[FailureInfo]):
    """Persists the failure reason as JSONB; NULL while the task has not failed."""

    impl = JSONB
    cache_ok = True

    @override
    def process_bind_param(
        self,
        value: FailureInfo | None,
        dialect: Dialect,
    ) -> dict[str, Any] | None:
        if value is None:
            return None
        return {"code": value.code, "message": value.message}

    @override
    def process_result_value(
        self,
        value: dict[str, Any] | None,
        dialect: Dialect,
    ) -> FailureInfo | None:
        if value is None:
            return None
        return FailureInfo(code=value["code"], message=value["message"])


class IndexingTaskStatusType(TypeDecorator[IndexingTaskStatus]):
    """Persists the task status as its ``StrEnum`` value.

    A plain text column rather than a native database enum: adding a state is
    then a code change, not a migration. Rebuilding the enum on load is what
    keeps ``status.is_terminal`` working on a loaded aggregate.
    """

    impl = Text
    cache_ok = True

    @override
    def process_bind_param(
        self,
        value: IndexingTaskStatus | None,
        dialect: Dialect,
    ) -> str | None:
        return value.value if value is not None else None

    @override
    def process_result_value(
        self,
        value: str | None,
        dialect: Dialect,
    ) -> IndexingTaskStatus | None:
        return IndexingTaskStatus(value) if value is not None else None


class QueryTextType(TypeDecorator[QueryText]):
    """Persists the recorded query text as plain TEXT."""

    impl = Text
    cache_ok = True

    @override
    def process_bind_param(
        self,
        value: QueryText | None,
        dialect: Dialect,
    ) -> str | None:
        return value.content if value is not None else None

    @override
    def process_result_value(
        self,
        value: str | None,
        dialect: Dialect,
    ) -> QueryText | None:
        return QueryText(content=value) if value is not None else None


class CategoryLabelType(TypeDecorator[CategoryLabel]):
    """Persists the recorded category as plain TEXT; NULL when unfiltered."""

    impl = Text
    cache_ok = True

    @override
    def process_bind_param(
        self,
        value: CategoryLabel | None,
        dialect: Dialect,
    ) -> str | None:
        return value.value if value is not None else None

    @override
    def process_result_value(
        self,
        value: str | None,
        dialect: Dialect,
    ) -> CategoryLabel | None:
        return CategoryLabel(value=value) if value is not None else None


class QueryKindType(TypeDecorator[QueryKind]):
    """Persists which entry point served the query, as its ``StrEnum`` value."""

    impl = Text
    cache_ok = True

    @override
    def process_bind_param(
        self,
        value: QueryKind | None,
        dialect: Dialect,
    ) -> str | None:
        return value.value if value is not None else None

    @override
    def process_result_value(
        self,
        value: str | None,
        dialect: Dialect,
    ) -> QueryKind | None:
        return QueryKind(value) if value is not None else None


class QueryStatusType(TypeDecorator[QueryStatus]):
    """Persists whether serving the query completed, as its ``StrEnum`` value."""

    impl = Text
    cache_ok = True

    @override
    def process_bind_param(
        self,
        value: QueryStatus | None,
        dialect: Dialect,
    ) -> str | None:
        return value.value if value is not None else None

    @override
    def process_result_value(
        self,
        value: str | None,
        dialect: Dialect,
    ) -> QueryStatus | None:
        return QueryStatus(value) if value is not None else None


class ErrorCodeType(TypeDecorator[ErrorCode]):
    """Persists the failure's code as plain TEXT; NULL when the query succeeded."""

    impl = Text
    cache_ok = True

    @override
    def process_bind_param(
        self,
        value: ErrorCode | None,
        dialect: Dialect,
    ) -> str | None:
        return value.value if value is not None else None

    @override
    def process_result_value(
        self,
        value: str | None,
        dialect: Dialect,
    ) -> ErrorCode | None:
        return ErrorCode(value=value) if value is not None else None


class LatencyType(TypeDecorator[Latency]):
    """Persists a measured duration as an integer number of milliseconds."""

    impl = Integer
    cache_ok = True

    @override
    def process_bind_param(
        self,
        value: Latency | None,
        dialect: Dialect,
    ) -> int | None:
        return value.milliseconds if value is not None else None

    @override
    def process_result_value(
        self,
        value: int | None,
        dialect: Dialect,
    ) -> Latency | None:
        return Latency(milliseconds=value) if value is not None else None
