"""Taskiq scheduler entry point.

Run with::

    taskiq scheduler answer_service.scheduler_app:scheduler
"""

import logging
from typing import Final

from taskiq import AsyncBroker, ScheduleSource, TaskiqScheduler

from answer_service.setup.bootstrap.setups.configs_setup import setup_configs
from answer_service.setup.bootstrap.setups.scheduler_setup import (
    setup_schedule_source,
    setup_scheduler,
)
from answer_service.worker_app import create_worker_taskiq_app

logger: Final[logging.Logger] = logging.getLogger(__name__)


def create_scheduler_taskiq_app() -> TaskiqScheduler:
    """Builds the scheduler that fires the cron tasks.

    Reuses the worker's broker so both sides agree on task names and transport;
    a separately built broker could drift and silently fire nothing. The
    scheduler only enqueues — the worker process still does the work.
    """
    configs = setup_configs()
    worker_broker: AsyncBroker = create_worker_taskiq_app()
    schedule_source: ScheduleSource = setup_schedule_source(configs.redis)
    return setup_scheduler(broker=worker_broker, schedule_source=schedule_source)


scheduler: Final[TaskiqScheduler] = create_scheduler_taskiq_app()
