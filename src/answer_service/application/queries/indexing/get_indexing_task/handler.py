import logging
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

logger: Final[logging.Logger] = logging.getLogger(__name__)


class GetIndexingTaskHandler(QueryHandler[GetIndexingTaskQuery, IndexingTaskView]):
    """Returns the status of one indexing run.

    Reads through the query gateway, so polling never instantiates the
    aggregate and never opens a write transaction.
    """

    def __init__(self, task_query_gateway: IndexingTaskQueryGateway) -> None:
        self._task_query_gateway: Final[IndexingTaskQueryGateway] = task_query_gateway

    @override
    async def handle(self, query: GetIndexingTaskQuery) -> IndexingTaskView:
        logger.info("get_indexing_task: reading task %s", query.task_id)

        view = await self._task_query_gateway.read_by_id(query.task_id)
        if view is None:
            logger.warning("get_indexing_task: task %s not found", query.task_id)
            msg = f"Indexing task '{query.task_id}' not found."
            raise IndexingTaskNotFoundError(msg)

        logger.info(
            "get_indexing_task: task %s is %s",
            query.task_id,
            view.status,
        )
        return view
