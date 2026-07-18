"""In-memory stand-ins for the persistence gateways.

They store aggregates by identity and hand back the *same* object, which mirrors
an identity-mapped session: a handler that reads an aggregate and mutates it does
not need to call ``update`` for the change to be visible. ``update`` calls are
still recorded so tests can assert a handler wrote through the gateway.
"""

from collections.abc import Sequence
from typing import final, override
from uuid import UUID

from answer_service.application.common.ports.gateways import (
    IndexingTaskCommandGateway,
    QACatalogCommandGateway,
    QACatalogQueryGateway,
)
from answer_service.application.common.ports.outbox import (
    OutboxCommandGateway,
    OutboxMessage,
)
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
