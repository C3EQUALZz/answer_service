import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Final, cast

import uvicorn
from dishka import AsyncContainer
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from sqlalchemy.orm import clear_mappers
from taskiq import AsyncBroker

from answer_service._version import __version__
from answer_service.setup.bootstrap.setups.configs_setup import (
    AppConfigs,
    make_container_context,
    setup_configs,
)
from answer_service.setup.bootstrap.setups.database_setup import setup_map_tables
from answer_service.setup.bootstrap.setups.http_setup import (
    setup_exc_handlers,
    setup_http_middlewares,
    setup_http_routes,
)
from answer_service.setup.bootstrap.setups.logging_setup import configure_logging
from answer_service.setup.bootstrap.setups.task_manager_setup import (
    setup_task_manager,
    setup_task_manager_tasks,
)
from answer_service.setup.ioc.containers import make_container

logger: Final[logging.Logger] = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Starts and stops what the process owns for its whole lifetime."""
    task_manager: AsyncBroker = cast("AsyncBroker", app.state.task_manager)
    container: AsyncContainer = cast("AsyncContainer", app.state.dishka_container)

    if not task_manager.is_worker_process:
        logger.info("Starting taskiq broker")
        await task_manager.startup()

    try:
        yield
    finally:
        if not task_manager.is_worker_process:
            logger.info("Shutting down taskiq broker")
            await task_manager.shutdown()

        clear_mappers()
        await container.close()


def create_fastapi_app() -> FastAPI:  # pragma: no cover
    """Builds the HTTP application with everything wired in."""
    configs: AppConfigs = setup_configs()
    configure_logging(configs.logging)
    setup_map_tables()

    task_manager: AsyncBroker = setup_task_manager(
        taskiq_config=configs.taskiq,
        nats_config=configs.nats,
        redis_config=configs.redis,
    )
    setup_task_manager_tasks(task_manager)

    app: FastAPI = FastAPI(
        lifespan=lifespan,
        title="answer_service",
        version=__version__,
        root_path="/api",
        debug=configs.asgi.fastapi_debug,
    )
    app.state.task_manager = task_manager

    container: AsyncContainer = make_container(
        make_container_context(configs, task_manager),
    )

    setup_http_routes(app)
    setup_exc_handlers(app)
    setup_http_middlewares(app, asgi_config=configs.asgi)
    setup_dishka(container, app)

    logger.info("App created", extra={"app_version": app.version})
    return app


if __name__ == "__main__":  # pragma: no cover
    asgi_config = setup_configs().asgi
    uvicorn.run(
        create_fastapi_app(),
        host=asgi_config.host,
        port=asgi_config.port,
        loop="uvloop" if sys.platform != "win32" else "asyncio",
    )
