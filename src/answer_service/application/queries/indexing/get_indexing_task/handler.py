from typing import Final, override

from answer_service.application.common.mediator.handlers import QueryHandler
from answer_service.application.common.ports.gateways import (
    IndexingTaskQueryGateway,
    IndexingTaskView,
)
from answer_service.application.error import IndexingTaskNotFoundError
from answer_service.application.queries.indexing.get_indexing_task.query import (
    GetIndexingTaskQuery,
)


class GetIndexingTaskHandler(QueryHandler[GetIndexingTaskQuery, IndexingTaskView]):
    """Returns the status of one indexing run.

    Reads through the query gateway, so polling never instantiates the
    aggregate and never opens a write transaction.
    """

    def __init__(self, task_query_gateway: IndexingTaskQueryGateway) -> None:
        self._task_query_gateway: Final[IndexingTaskQueryGateway] = task_query_gateway

    @override
    async def handle(self, query: GetIndexingTaskQuery) -> IndexingTaskView:
        view = await self._task_query_gateway.read_by_id(query.task_id)
        if view is None:
            msg = f"Indexing task '{query.task_id}' not found."
            raise IndexingTaskNotFoundError(msg)
        return view
