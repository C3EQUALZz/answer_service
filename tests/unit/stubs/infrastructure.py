"""Recording stand-ins for the infrastructure-facing ports.

Several stubs share a :class:`CallJournal` so a test can assert *ordering across*
ports — that events were published before the transaction committed, that a
rollback happened instead of a commit, and so on. Ordering is the whole point of
the pipeline tests, and it is invisible if each stub only records its own calls.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, final, override
from uuid import UUID, uuid4

from taskiq import ScheduleSource, ScheduledTask

from answer_service.application.common.ports.outbox import (
    EventBus,
    EventSerializer,
    OutboxMessage,
    OutboxPublisher,
)
from answer_service.application.common.ports.search import (
    DenseRetriever,
    IndexDocument,
    LexicalRetriever,
    SearchIndexWriter,
)
from answer_service.application.common.ports.task_manager.payloads.base import (
    TaskPayload,
)
from answer_service.application.common.ports.task_manager.task_id import (
    TaskID,
    TaskInfo,
    TaskKey,
)
from answer_service.application.common.ports.task_manager.task_manager import (
    TaskScheduler,
)
from answer_service.application.common.ports.transaction_manager import (
    TransactionManager,
)
from answer_service.domain.analytics.value_objects.query_log_id import QueryLogId
from answer_service.domain.common.error import AppError
from answer_service.domain.common.event import Event
from answer_service.domain.indexing.value_objects.external_id import ExternalId
from answer_service.domain.indexing.value_objects.task_id import TaskId
from answer_service.domain.search.value_objects.scored_candidate import ScoredCandidate
from answer_service.domain.search.value_objects.search_criteria import SearchCriteria


class BrokerUnavailableError(AppError):
    """Stand-in for a transport failure inside the relay."""


@dataclass(slots=True)
class CallJournal:
    """Ordered log of the cross-port calls made during one command."""

    entries: list[str] = field(default_factory=list)

    def record(self, name: str) -> None:
        self.entries.append(name)


@final
class RecordingTransactionManager(TransactionManager):
    def __init__(self, journal: CallJournal) -> None:
        self._journal = journal

    @override
    async def flush(self) -> None:
        self._journal.record("flush")

    @override
    async def commit(self) -> None:
        self._journal.record("commit")

    @override
    async def rollback(self) -> None:
        self._journal.record("rollback")


@final
class RecordingEventBus(EventBus):
    def __init__(self, journal: CallJournal) -> None:
        self._journal = journal
        self.published: list[Event] = []

    @override
    async def publish(self, events: Iterable[Event]) -> None:
        self.published.extend(events)
        self._journal.record("publish")


@final
class RecordingTaskScheduler(TaskScheduler):
    def __init__(self) -> None:
        self.scheduled: list[tuple[TaskID, TaskPayload]] = []

    @override
    async def schedule(self, task_id: TaskID, payload: TaskPayload) -> None:
        self.scheduled.append((task_id, payload))

    @override
    async def read_task_info(self, task_id: TaskID) -> TaskInfo | None:
        del task_id
        return None

    @override
    def make_task_id(self, key: TaskKey, value: Any) -> TaskID:
        return TaskID(f"{key}:{value}")


@final
class StubEventSerializer(EventSerializer):
    @override
    def serialize(self, event: Event) -> OutboxMessage:
        return OutboxMessage(
            id=uuid4(),
            event_type=event.event_type,
            payload="{}",
            created_at=datetime.now(UTC),
        )


@final
class RecordingOutboxPublisher(OutboxPublisher):
    """Publishes to a list; fails on the message ids it was told to reject."""

    def __init__(self, failing_ids: frozenset[UUID] = frozenset()) -> None:
        self._failing_ids = failing_ids
        self.published: list[OutboxMessage] = []

    @override
    async def publish(self, message: OutboxMessage) -> None:
        if message.id in self._failing_ids:
            msg = f"broker refused message '{message.id}'."
            raise BrokerUnavailableError(msg)
        self.published.append(message)


@final
class StubTaskIdGenerator:
    """Hands out preset task ids so assertions can name them."""

    def __init__(self, *task_ids: TaskId) -> None:
        self._task_ids = list(task_ids)

    def __call__(self) -> TaskId:
        return self._task_ids.pop(0) if self._task_ids else TaskId(uuid4())


@final
class RecordingSearchIndexWriter(SearchIndexWriter):
    """Records what reached the search index, in order."""

    def __init__(self) -> None:
        self.upserted: list[IndexDocument] = []
        self.deleted: list[ExternalId] = []

    @override
    async def upsert(self, documents: Sequence[IndexDocument]) -> None:
        self.upserted.extend(documents)

    @override
    async def delete(self, external_ids: Sequence[ExternalId]) -> None:
        self.deleted.extend(external_ids)


@final
class StubDenseRetriever(DenseRetriever):
    """Returns whatever the test staged, in the order it staged it."""

    def __init__(self) -> None:
        self.candidates: list[ScoredCandidate] = []
        self.criteria: list[SearchCriteria] = []

    @override
    async def retrieve(self, criteria: SearchCriteria) -> Sequence[ScoredCandidate]:
        self.criteria.append(criteria)
        return self.candidates


@final
class StubLexicalRetriever(LexicalRetriever):
    """Returns whatever the test staged, in the order it staged it."""

    def __init__(self) -> None:
        self.candidates: list[ScoredCandidate] = []
        self.criteria: list[SearchCriteria] = []

    @override
    async def retrieve(self, criteria: SearchCriteria) -> Sequence[ScoredCandidate]:
        self.criteria.append(criteria)
        return self.candidates


@final
class StubQueryLogIdGenerator:
    """Hands out fresh log ids; identity is never asserted on."""

    def __call__(self) -> QueryLogId:
        return QueryLogId(uuid4())


@final
class StubScheduleSource(ScheduleSource):
    """A schedule source the scheduler holds but these tests never exercise."""

    @override
    async def get_schedules(self) -> list[ScheduledTask]:
        return []
