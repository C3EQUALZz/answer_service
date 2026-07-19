from collections.abc import Iterable
from typing import Final

from dishka import AsyncContainer, Provider, make_async_container
from dishka.integrations.taskiq import TaskiqProvider

from answer_service.setup.ioc.providers import (
    configs_provider,
    database_provider,
    domain_provider,
    gateways_provider,
    handlers_provider,
    mediator_provider,
    pipelines_provider,
    task_manager_provider,
    vector_store_provider,
)


def setup_providers() -> Iterable[Provider]:
    """Every provider the application is assembled from.

    Split by concern rather than by layer: each function owns one kind of thing
    and states its own scope, so a lifetime mistake is visible in the file that
    made it instead of buried in one long list.
    """
    return (
        configs_provider(),
        database_provider(),
        vector_store_provider(),
        task_manager_provider(),
        domain_provider(),
        gateways_provider(),
        pipelines_provider(),
        handlers_provider(),
        mediator_provider(),
        TaskiqProvider(),
    )


def make_container(context: dict[type, object]) -> AsyncContainer:
    """Builds the application container.

    *context* carries the objects created before the container exists — the
    loaded configs and the taskiq broker — keyed by the type they are provided
    as.
    """
    providers: Final[Iterable[Provider]] = tuple(setup_providers())
    return make_async_container(*providers, context=context)
