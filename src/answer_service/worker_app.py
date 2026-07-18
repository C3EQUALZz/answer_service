"""Taskiq worker entry point.

Run with::

    taskiq worker answer_service.worker_app:broker
"""

import logging
from typing import Final

from dishka import AsyncContainer
from dishka.integrations.taskiq import setup_dishka
from sqlalchemy.orm import clear_mappers
from taskiq import AsyncBroker, TaskiqEvents, TaskiqState

from answer_service.setup.bootstrap.setups.configs_setup import (
    AppConfigs,
    make_container_context,
    setup_configs,
)
from answer_service.setup.bootstrap.setups.database_setup import setup_map_tables
from answer_service.setup.bootstrap.setups.logging_setup import configure_logging
from answer_service.setup.bootstrap.setups.task_manager_setup import (
    setup_task_manager,
    setup_task_manager_middlewares,
    setup_task_manager_tasks,
)
from answer_service.setup.ioc.containers import make_container

logger: Final[logging.Logger] = logging.getLogger(__name__)


def create_worker_taskiq_app() -> AsyncBroker:
    """Builds the broker the worker process serves tasks from.

    Retry middleware is applied here and not in the API process: only the side
    that executes a task can retry it, and the API never does.
    """
    configs: AppConfigs = setup_configs()
    configure_logging(configs.logging)

    worker_broker: AsyncBroker = setup_task_manager(
        taskiq_config=configs.taskiq,
        nats_config=configs.nats,
        redis_config=configs.redis,
    )
    worker_broker = setup_task_manager_middlewares(
        broker=worker_broker,
        taskiq_config=configs.taskiq,
    )
    setup_task_manager_tasks(broker=worker_broker)

    async def startup(state: TaskiqState) -> None:  # ruff:ignore[unused-function-argument, unused-async]
        # Mapped on worker startup rather than at import: taskiq forks workers,
        # and mapping in the parent would be inherited half-initialised.
        setup_map_tables()
        logger.info("Taskiq worker started")

    async def shutdown(state: TaskiqState) -> None:  # ruff:ignore[unused-function-argument, unused-async]
        clear_mappers()
        logger.info("Taskiq worker stopped")

    worker_broker.on_event(TaskiqEvents.WORKER_STARTUP)(startup)
    worker_broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)(shutdown)

    container: AsyncContainer = make_container(
        make_container_context(configs, worker_broker),
    )
    setup_dishka(container, broker=worker_broker)

    return worker_broker


broker: Final[AsyncBroker] = create_worker_taskiq_app()
