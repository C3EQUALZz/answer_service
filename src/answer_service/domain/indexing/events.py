from dataclasses import dataclass

from answer_service.domain.common.event import Event
from answer_service.domain.indexing.value_objects.external_id import ExternalId
from answer_service.domain.indexing.value_objects.failure_info import FailureInfo
from answer_service.domain.indexing.value_objects.sync_stats import SyncStats
from answer_service.domain.indexing.value_objects.task_id import TaskId


@dataclass(frozen=True, kw_only=True)
class QAPairAdded(Event):
    external_id: ExternalId


@dataclass(frozen=True, kw_only=True)
class QAPairContentUpdated(Event):
    external_id: ExternalId


@dataclass(frozen=True, kw_only=True)
class QAPairRemoved(Event):
    external_id: ExternalId


@dataclass(frozen=True, kw_only=True)
class IndexingTaskQueued(Event):
    task_id: TaskId


@dataclass(frozen=True, kw_only=True)
class IndexingStarted(Event):
    task_id: TaskId


@dataclass(frozen=True, kw_only=True)
class IndexingCompleted(Event):
    task_id: TaskId
    stats: SyncStats


@dataclass(frozen=True, kw_only=True)
class IndexingFailed(Event):
    task_id: TaskId
    failure: FailureInfo
