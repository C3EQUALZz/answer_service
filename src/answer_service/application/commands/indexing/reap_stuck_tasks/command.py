from dataclasses import dataclass, field
from datetime import timedelta
from typing import Final

from answer_service.application.common.mediator.markers import Command

DEFAULT_BATCH_SIZE: Final[int] = 50
DEFAULT_STUCK_AFTER: Final[timedelta] = timedelta(hours=1)


@dataclass(frozen=True, slots=True)
class ReapStuckTasksResponse:
    """How many abandoned runs this tick settled, for the worker log."""

    reaped: int


@dataclass(frozen=True, slots=True)
class ReapStuckTasksCommand(Command[ReapStuckTasksResponse]):
    """Settle indexing runs whose worker died before finishing them.

    ``stuck_after`` has to outlast the slowest legitimate run: a task still
    working when the reaper reaches it would be failed underneath itself, and
    the sync would then commit against a task that is already terminal. An hour
    is far beyond any observed run over the sample catalog.

    Dispatched by the scheduler on a cron tick. Safe on several replicas — the
    gateway claims rows with ``SKIP LOCKED``.
    """

    stuck_after: timedelta = field(default=DEFAULT_STUCK_AFTER)
    batch_size: int = field(default=DEFAULT_BATCH_SIZE)
