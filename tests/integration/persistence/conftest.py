from collections.abc import Awaitable, Callable

import pytest

from answer_service.application.common.ports.gateways import (
    IndexingTaskCommandGateway,
    QACatalogCommandGateway,
)
from answer_service.application.common.ports.transaction_manager import (
    TransactionManager,
)
from answer_service.domain.indexing.entities.indexing_task import IndexingTask
from answer_service.domain.indexing.entities.qa_pair import QAPair
from answer_service.domain.indexing.value_objects.external_id import ExternalId
from answer_service.domain.indexing.value_objects.task_id import TaskId
from tests.unit.factories.domain_factories import (
    SOURCE_UPDATED_AT,
    make_events_collection,
    make_qa_content,
)

type TaskStorer = Callable[[IndexingTask], Awaitable[TaskId]]
type PairStorer = Callable[..., Awaitable[None]]
type PairBuilder = Callable[..., QAPair]


@pytest.fixture()
def store_indexing_task(
    arrange_indexing_tasks: IndexingTaskCommandGateway,
    arrange_transaction: TransactionManager,
) -> TaskStorer:
    """Commits a task before the test reads it back."""

    async def store(task: IndexingTask) -> TaskId:
        await arrange_indexing_tasks.add(task)
        await arrange_transaction.commit()
        return task.id

    return store


@pytest.fixture()
def make_pair() -> PairBuilder:
    """Builds a registered pair with its own events collection."""

    def build(external_id: str, **content: str) -> QAPair:
        return QAPair.register(
            external_id=ExternalId(value=external_id),
            content=make_qa_content(**content),
            source_updated_at=SOURCE_UPDATED_AT,
            events_collection=make_events_collection(),
        )

    return build


@pytest.fixture()
def store_qa_pairs(
    arrange_catalog: QACatalogCommandGateway,
    arrange_transaction: TransactionManager,
) -> PairStorer:
    async def store(*pairs: QAPair) -> None:
        for pair in pairs:
            await arrange_catalog.add(pair)
        await arrange_transaction.commit()

    return store
