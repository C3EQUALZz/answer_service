import logging
from datetime import UTC, datetime
from typing import Final, override

from answer_service.application.commands.indexing.reap_stuck_tasks.command import (
    ReapStuckTasksCommand,
    ReapStuckTasksResponse,
)
from answer_service.application.common.mediator.handlers import CommandHandler
from answer_service.application.common.ports.gateways import IndexingTaskCommandGateway
from answer_service.domain.indexing.value_objects.failure_info import FailureInfo

logger: Final[logging.Logger] = logging.getLogger(__name__)

ABANDONED_FAILURE_CODE: Final[str] = "TaskAbandoned"


class ReapStuckTasksHandler(
    CommandHandler[ReapStuckTasksCommand, ReapStuckTasksResponse],
):
    """Fails indexing runs that have been ``RUNNING`` for too long.

    ``RUNNING`` is committed in its own transaction before the heavy sync, so
    the status API can show it. That is also what makes it a trap: if the worker
    dies during the sync, the row stays ``RUNNING`` and nothing else will ever
    touch it. The task looks alive forever, and the caller polling it never
    learns that it should upload again.

    The run is recorded as ``FAILED`` rather than requeued. Its work rolled back
    with the crashed transaction, so there is nothing to resume, and re-running
    a sync is the caller's decision — a reaper that silently retried could
    reprocess a file the customer has since replaced.
    """

    def __init__(self, task_gateway: IndexingTaskCommandGateway) -> None:
        self._task_gateway: Final[IndexingTaskCommandGateway] = task_gateway

    @override
    async def handle(self, command: ReapStuckTasksCommand) -> ReapStuckTasksResponse:
        cutoff = datetime.now(UTC) - command.stuck_after

        stuck = await self._task_gateway.read_stuck(
            started_before=cutoff,
            limit=command.batch_size,
        )
        if not stuck:
            logger.debug("reap_stuck_tasks: nothing stuck before %s", cutoff)
            return ReapStuckTasksResponse(reaped=0)

        logger.warning(
            "reap_stuck_tasks: %d run(s) still RUNNING since before %s",
            len(stuck),
            cutoff,
        )

        for task in stuck:
            task.abandon(
                FailureInfo(
                    code=ABANDONED_FAILURE_CODE,
                    message=(
                        f"The run was still RUNNING after {command.stuck_after}; "
                        f"its worker did not finish it."
                    ),
                ),
            )
            await self._task_gateway.update(task)
            logger.warning(
                "reap_stuck_tasks: abandoned task %s, started at %s",
                task.id,
                task.started_at,
            )

        return ReapStuckTasksResponse(reaped=len(stuck))
