"""In-memory stand-ins for the persistence gateways.

They store aggregates by identity and hand back the *same* object, which mirrors
an identity-mapped session: a handler that reads an aggregate and mutates it does
not need to call ``update`` for the change to be visible. ``update`` calls are
still recorded so tests can assert a handler wrote through the gateway.
"""

from collections import Counter
from collections.abc import Iterable, Sequence
from typing import final, override
from uuid import UUID

from answer_service.application.common.ports.gateways import (
    AnalyticsCommandGateway,
    AnalyticsQueryGateway,
    CatalogStatistics,
    IndexingTaskCommandGateway,
    IndexingTaskQueryGateway,
    IndexingTaskView,
    QACatalogCommandGateway,
    QACatalogQueryGateway,
    QAPairView,
    QueryFrequency,
    QueryStatistics,
)
from answer_service.application.common.ports.outbox import (
    OutboxCommandGateway,
    OutboxMessage,
)
from answer_service.application.common.query_params.pagination import Pagination
from answer_service.application.common.query_params.sorting import SortingOrder
from answer_service.domain.analytics.entities.query_log import QueryLog
from answer_service.domain.analytics.value_objects.period import Period
from answer_service.domain.indexing.entities.indexing_task import IndexingTask
from answer_service.domain.indexing.entities.qa_pair import QAPair
from answer_service.domain.indexing.value_objects.content_hash import ContentHash
from answer_service.domain.indexing.value_objects.external_id import ExternalId
from answer_service.domain.indexing.value_objects.task_id import TaskId


@final
class InMemoryIndexingTaskGateway(IndexingTaskCommandGateway):
    def __init__(self) -> None:
        self.tasks: dict[TaskId, IndexingTask] = {}
        self.updated: list[TaskId] = []

    @override
    async def add(self, task: IndexingTask) -> None:
        self.tasks[task.id] = task

    @override
    async def read_by_id(self, task_id: TaskId) -> IndexingTask | None:
        return self.tasks.get(task_id)

    @override
    async def update(self, task: IndexingTask) -> None:
        self.tasks[task.id] = task
        self.updated.append(task.id)

    @override
    async def delete_by_id(self, task_id: TaskId) -> None:
        self.tasks.pop(task_id, None)


@final
class InMemoryQACatalog(QACatalogCommandGateway, QACatalogQueryGateway):
    """Backs both catalog gateways so a test can seed once and assert once."""

    def __init__(self) -> None:
        self.pairs: dict[ExternalId, QAPair] = {}
        self.added: list[ExternalId] = []
        self.updated: list[ExternalId] = []
        self.deleted: list[ExternalId] = []

    @override
    async def add(self, pair: QAPair) -> None:
        self.pairs[pair.id] = pair
        self.added.append(pair.id)

    @override
    async def read_by_id(self, external_id: ExternalId) -> QAPair | None:
        return self.pairs.get(external_id)

    @override
    async def update(self, pair: QAPair) -> None:
        self.pairs[pair.id] = pair
        self.updated.append(pair.id)

    @override
    async def delete_by_id(self, external_id: ExternalId) -> None:
        self.pairs.pop(external_id, None)
        self.deleted.append(external_id)

    @override
    async def read_fingerprints(self) -> dict[ExternalId, ContentHash]:
        return {
            external_id: pair.content.fingerprint
            for external_id, pair in self.pairs.items()
        }

    @override
    async def read_views(
        self,
        external_ids: Iterable[ExternalId],
    ) -> dict[ExternalId, QAPairView]:
        return {
            external_id: QAPairView(
                external_id=external_id.value,
                question=pair.content.question.content,
                answer=pair.content.answer.content,
                category=pair.content.category.value,
            )
            for external_id in external_ids
            if (pair := self.pairs.get(external_id)) is not None
        }

    @override
    async def read_statistics(self) -> CatalogStatistics:
        per_category = Counter(
            pair.content.category.value for pair in self.pairs.values()
        )
        return CatalogStatistics(
            total_pairs=len(self.pairs),
            pairs_per_category=dict(per_category),
        )


@final
class InMemoryOutboxGateway(OutboxCommandGateway):
    def __init__(self) -> None:
        self.messages: list[OutboxMessage] = []
        self.processed: list[UUID] = []

    @override
    async def add(self, message: OutboxMessage) -> None:
        self.messages.append(message)

    @override
    async def read_pending(self, limit: int) -> Sequence[OutboxMessage]:
        pending = [m for m in self.messages if m.id not in self.processed]
        return pending[:limit]

    @override
    async def mark_processed(self, message_id: UUID) -> None:
        self.processed.append(message_id)


@final
class InMemoryAnalytics(AnalyticsCommandGateway, AnalyticsQueryGateway):
    """Backs both analytics gateways, aggregating in Python.

    The production gateway pushes these aggregations into SQL; here they are
    written out so a test can state the expected numbers directly.
    """

    def __init__(self) -> None:
        self.logs: list[QueryLog] = []

    @override
    async def add(self, query_log: QueryLog) -> None:
        self.logs.append(query_log)

    @override
    async def read_statistics(self, period: Period) -> QueryStatistics:
        logs = self._within(period)
        if not logs:
            return QueryStatistics(total=0, unanswered=0, average_latency_ms=0.0)

        latencies = [log.latency.milliseconds for log in logs]
        return QueryStatistics(
            total=len(logs),
            unanswered=sum(1 for log in logs if log.is_unanswered),
            average_latency_ms=sum(latencies) / len(latencies),
        )

    @override
    async def read_unanswered_queries(
        self,
        period: Period,
        pagination: Pagination,
        sorting_order: SortingOrder,
    ) -> Sequence[QueryFrequency]:
        return self._rank(
            [log for log in self._within(period) if log.is_unanswered],
            pagination,
            sorting_order,
        )

    @override
    async def read_popular_queries(
        self,
        period: Period,
        pagination: Pagination,
        sorting_order: SortingOrder,
    ) -> Sequence[QueryFrequency]:
        return self._rank(self._within(period), pagination, sorting_order)

    def _within(self, period: Period) -> list[QueryLog]:
        return [log for log in self.logs if period.contains(log.occurred_at)]

    @staticmethod
    def _rank(
        logs: list[QueryLog],
        pagination: Pagination,
        sorting_order: SortingOrder,
    ) -> Sequence[QueryFrequency]:
        counts = Counter(log.text.content for log in logs)
        # Ties broken by text, mirroring the SQL gateway — otherwise paging
        # through the report could repeat or skip a row.
        ranked = sorted(
            counts.items(),
            key=lambda item: (
                item[1] if sorting_order is SortingOrder.ASC else -item[1],
                item[0],
            ),
        )
        offset = pagination.offset or 0
        window = ranked[offset:]
        if pagination.limit is not None:
            window = window[: pagination.limit]
        return [
            QueryFrequency(text=text, occurrences=occurrences)
            for text, occurrences in window
        ]


@final
class InMemoryIndexingTaskQueryGateway(IndexingTaskQueryGateway):
    def __init__(self) -> None:
        self.views: dict[TaskId, IndexingTaskView] = {}

    @override
    async def read_by_id(self, task_id: TaskId) -> IndexingTaskView | None:
        return self.views.get(task_id)
