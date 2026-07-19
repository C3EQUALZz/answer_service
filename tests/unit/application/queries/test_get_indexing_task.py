import pytest

from answer_service.application.error import IndexingTaskNotFoundError
from answer_service.application.queries.indexing.get_indexing_task.handler import (
    GetIndexingTaskHandler,
)
from answer_service.application.queries.indexing.get_indexing_task.query import (
    GetIndexingTaskQuery,
)
from answer_service.domain.indexing.value_objects.task_status import IndexingTaskStatus
from tests.unit.factories.domain_factories import (
    make_indexing_task_view,
    make_task_id,
)
from tests.unit.stubs.gateways import InMemoryIndexingTaskQueryGateway


async def test_returns_the_task_status(
    get_indexing_task_handler: GetIndexingTaskHandler,
    task_query_gateway: InMemoryIndexingTaskQueryGateway,
) -> None:
    task_id = make_task_id()
    task_query_gateway.views[task_id] = make_indexing_task_view(task_id)

    view = await get_indexing_task_handler.handle(GetIndexingTaskQuery(task_id=task_id))

    assert view.task_id == task_id
    assert view.status is IndexingTaskStatus.SUCCEEDED
    assert view.created == 2
    assert view.skipped == 5
    assert view.is_finished


@pytest.mark.parametrize(
    ("status", "finished"),
    (
        (IndexingTaskStatus.QUEUED, False),
        (IndexingTaskStatus.RUNNING, False),
        (IndexingTaskStatus.SUCCEEDED, True),
        (IndexingTaskStatus.FAILED, True),
    ),
)
async def test_reports_whether_polling_can_stop(
    status: IndexingTaskStatus,
    *,
    finished: bool,
    get_indexing_task_handler: GetIndexingTaskHandler,
    task_query_gateway: InMemoryIndexingTaskQueryGateway,
) -> None:
    """Clients poll this endpoint, so the terminal flag is its whole contract."""
    task_id = make_task_id()
    task_query_gateway.views[task_id] = make_indexing_task_view(task_id, status)

    view = await get_indexing_task_handler.handle(GetIndexingTaskQuery(task_id=task_id))

    assert view.is_finished is finished


async def test_raises_for_an_unknown_task(
    get_indexing_task_handler: GetIndexingTaskHandler,
) -> None:
    query = GetIndexingTaskQuery(task_id=make_task_id())

    with pytest.raises(IndexingTaskNotFoundError):
        await get_indexing_task_handler.handle(query)
