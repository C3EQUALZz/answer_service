from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Self, final

from answer_service.domain.common.aggregate import Aggregate
from answer_service.domain.indexing.errors import InvalidTaskTransitionError
from answer_service.domain.indexing.events import (
    IndexingCompleted,
    IndexingFailed,
    IndexingStarted,
    IndexingTaskQueued,
)
from answer_service.domain.indexing.value_objects.failure_info import FailureInfo
from answer_service.domain.indexing.value_objects.source_reference import SourceReference
from answer_service.domain.indexing.value_objects.sync_stats import SyncStats
from answer_service.domain.indexing.value_objects.task_id import TaskId
from answer_service.domain.indexing.value_objects.task_status import IndexingTaskStatus

if TYPE_CHECKING:
    from answer_service.domain.common.events_collection import EventsCollection


@final
@dataclass(eq=False, kw_only=True)
class IndexingTask(Aggregate[TaskId]):
    """A single synchronization run of the source file with the search stores.

    Records the source that was synced, the lifecycle
    (``QUEUED -> RUNNING -> SUCCEEDED | FAILED``), timings and the resulting
    :class:`SyncStats`, so it can back the task-status API.
    """

    source: SourceReference
    status: IndexingTaskStatus = field(default=IndexingTaskStatus.QUEUED)
    started_at: datetime | None = field(default=None)
    finished_at: datetime | None = field(default=None)
    stats: SyncStats = field(default_factory=SyncStats.empty)
    failure: FailureInfo | None = field(default=None)

    @classmethod
    def queue(
        cls,
        task_id: TaskId,
        source: SourceReference,
        events_collection: EventsCollection,
    ) -> Self:
        task = cls(id=task_id, source=source, events_collection=events_collection)
        task.events_collection.add_event(IndexingTaskQueued(task_id=task_id))
        return task

    def start(self) -> None:
        self._ensure_status(IndexingTaskStatus.QUEUED)
        self.status = IndexingTaskStatus.RUNNING
        self.started_at = datetime.now(UTC)
        self.events_collection.add_event(IndexingStarted(task_id=self.id))

    def complete(self, stats: SyncStats) -> None:
        self._ensure_status(IndexingTaskStatus.RUNNING)
        self.status = IndexingTaskStatus.SUCCEEDED
        self.stats = stats
        self.finished_at = datetime.now(UTC)
        self.events_collection.add_event(
            IndexingCompleted(task_id=self.id, stats=stats),
        )

    def abandon(self, failure: FailureInfo) -> None:
        """Settles a run whose worker never came back.

        Only a ``RUNNING`` task can be abandoned. A queued one has not been
        picked up yet and is still someone's to run, and a terminal one already
        has its answer — narrowing the transition here is what stops a reaper
        sweeping work that is merely slow to start.
        """
        self._ensure_status(IndexingTaskStatus.RUNNING)
        self.fail(failure)

    def fail(self, failure: FailureInfo) -> None:
        if self.status.is_terminal:
            msg = f"Task '{self.id}' is already {self.status} and cannot fail."
            raise InvalidTaskTransitionError(msg)
        self.status = IndexingTaskStatus.FAILED
        self.finished_at = datetime.now(UTC)
        self.failure = failure
        self.events_collection.add_event(
            IndexingFailed(task_id=self.id, failure=failure),
        )

    def _ensure_status(self, expected: IndexingTaskStatus) -> None:
        if self.status != expected:
            msg = (
                f"Task '{self.id}' must be {expected} for this operation "
                f"(current: {self.status})."
            )
            raise InvalidTaskTransitionError(msg)
